"""Explicit, dependency-injected agent state machine."""

from __future__ import annotations

import time

from mitecoder.agent.budget import BudgetManager
from mitecoder.agent.prompts import SYSTEM, build_prompt
from mitecoder.agent.protocol import parse_action
from mitecoder.agent.result import RunResult
from mitecoder.agent.state import AgentState
from mitecoder.inference.base import InferenceBackend, InferenceRequest
from mitecoder.metrics.collector import MetricsCollector
from mitecoder.repository.workspace import Workspace
from mitecoder.retrieval.base import RetrievalStrategy
from mitecoder.retrieval.context_builder import ContextBuilder
from mitecoder.tools.registry import ToolRegistry
from mitecoder.tools.run_tests import RunTestsTool


class Agent:
    def __init__(
        self,
        backend: InferenceBackend,
        retriever: RetrievalStrategy,
        tools: ToolRegistry,
        budget: BudgetManager,
        metrics: MetricsCollector,
        context_builder: ContextBuilder,
        max_output_tokens: int,
    ) -> None:
        self.backend, self.retriever, self.tools = backend, retriever, tools
        self.budget, self.metrics, self.context_builder = budget, metrics, context_builder
        self.max_output_tokens = max_output_tokens
        self.state = AgentState.INITIALIZING

    def _transition(self, state: AgentState, step: int) -> None:
        self.state = state
        self.metrics.emit("state", state=state.value, step=step)

    def run(self, task: str, workspace: Workspace) -> RunResult:
        started, observation = time.monotonic(), "No tool has run yet."
        verification_passed = False
        mutation_made = False
        tests_blocked = False
        blocked_actions: set[str] = set()
        self._transition(AgentState.ANALYZING, 0)
        self._transition(AgentState.RETRIEVING, 0)
        items = self.retriever.retrieve(task, workspace)
        context = self.context_builder.build(items)
        self.budget.context_tokens = len(context) // 4
        while True:
            reason = self.budget.exhausted()
            if reason:
                self._transition(AgentState.BUDGET_EXHAUSTED, self.budget.steps)
                return self._result(
                    "BUDGET_EXHAUSTED", reason, "Execution budget exhausted.", started
                )
            self.budget.steps += 1
            step = self.budget.steps
            self._transition(AgentState.REQUESTING_ACTION, step)
            schemas = self.tools.schemas()
            if tests_blocked:
                mutation_actions = {"apply_patch", "replace_text", "write_file"}
                schemas = {
                    name: schema for name, schema in schemas.items() if name in mutation_actions
                }
            for blocked_action in blocked_actions:
                schemas.pop(blocked_action, None)
            if not mutation_made and not tests_blocked:
                schemas["answer"] = {
                    "type": "object",
                    "required": ["text"],
                    "properties": {"text": {"type": "string"}},
                }
            prompt = build_prompt(
                task,
                schemas,
                context,
                observation,
                allow_finish=verification_passed,
            )
            inference_started = time.monotonic()
            self.budget.llm_calls += 1
            try:
                response = self.backend.generate(
                    InferenceRequest(prompt, self.max_output_tokens, system_prompt=SYSTEM)
                )
            except Exception as exc:
                duration = (time.monotonic() - inference_started) * 1000
                self.metrics.emit(
                    "inference_error",
                    step=step,
                    duration_ms=duration,
                    error_type=type(exc).__name__,
                    message=str(exc),
                )
                self._transition(AgentState.FAILED, step)
                return self._result(
                    "FAILED",
                    "inference_error",
                    f"Local inference failed: {exc}",
                    started,
                )
            duration = (time.monotonic() - inference_started) * 1000
            self.budget.input_tokens += response.input_tokens or 0
            self.budget.output_tokens += response.output_tokens or 0
            self.metrics.emit(
                "inference",
                step=step,
                duration_ms=duration,
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                response_text=response.text,
            )
            self._transition(AgentState.VALIDATING_ACTION, step)
            try:
                action = parse_action(response.text, set(schemas))
            except Exception as exc:
                allowed = ", ".join(schemas)
                observation = (
                    f"{observation[-4500:]}\n\naction success=False\n"
                    f"Rejected model action: {exc}. Do not repeat it. "
                    f"Choose one of: {allowed}. Fix the diagnosed code before testing again."
                )
                self._transition(AgentState.OBSERVING, step)
                continue
            if action.action == "finish":
                if not verification_passed:
                    observation = "finish success=False\nRun the configured tests successfully before finishing."
                    self._transition(AgentState.OBSERVING, step)
                    continue
                summary = str(action.arguments.get("summary", action.summary))
                self._transition(AgentState.COMPLETED, step)
                result = self._result("COMPLETED", "finish", summary, started)
                result.verification_passed = True
                return result
            if action.action == "answer":
                answer = action.arguments.get("text")
                if not isinstance(answer, str) or not answer.strip() or len(answer) > 12_000:
                    observation = (
                        "answer success=False\nAnswer text must contain 1-12000 characters."
                    )
                    self._transition(AgentState.OBSERVING, step)
                    continue
                self._transition(AgentState.COMPLETED, step)
                return self._result("COMPLETED", "answered", answer.strip(), started)
            self._transition(AgentState.EXECUTING_TOOL, step)
            tool_started = time.monotonic()
            try:
                result = self.tools.get(action.action).execute(action.arguments)
            except Exception as exc:
                result_text, success = f"Tool rejected action: {exc}", False
            else:
                result_text, success = result.output, result.success
            self.budget.tool_calls += 1
            if action.action in {"apply_patch", "replace_text", "write_file"} and success:
                mutation_made = True
                blocked_actions.clear()
                verification_passed = False
                tests_blocked = False
                verification_started = time.monotonic()
                test_tool = self.tools.get("run_tests")
                if not isinstance(test_tool, RunTestsTool):
                    raise TypeError("run_tests must be a RunTestsTool")
                verification = test_tool.execute_all()
                commands_run = int(verification.metadata.get("commands_run", 1))
                self.budget.tool_calls += commands_run
                verification_passed = verification.success
                tests_blocked = not verification.success
                self.metrics.emit(
                    "tool_call",
                    step=step,
                    tool="run_tests",
                    success=verification.success,
                    automatic=True,
                    duration_ms=(time.monotonic() - verification_started) * 1000,
                    output=verification.output[-20_000:],
                )
                if verification.success:
                    self._transition(AgentState.COMPLETED, step)
                    completed = self._result(
                        "COMPLETED",
                        "tests_passed",
                        "Applied a change and the configured tests passed.",
                        started,
                    )
                    completed.verification_passed = True
                    return completed
                result_text = (
                    f"{result_text}\nAutomatic verification failed:\n{verification.output}"
                )
            elif action.action == "run_tests":
                verification_passed = success
                tests_blocked = not success
            if not success:
                blocked_actions.add(action.action)
            self.metrics.emit(
                "tool_call",
                step=step,
                tool=action.action,
                success=success,
                duration_ms=(time.monotonic() - tool_started) * 1000,
                output=result_text[-20_000:],
            )
            observation = f"{action.action} success={success}\n{result_text}"
            self._transition(AgentState.OBSERVING, step)

    def _result(self, status: str, reason: str, summary: str, started: float) -> RunResult:
        return RunResult(
            status,
            reason,
            summary,
            self.budget.steps,
            self.budget.llm_calls,
            self.budget.tool_calls,
            self.budget.input_tokens,
            self.budget.output_tokens,
            time.monotonic() - started,
        )
