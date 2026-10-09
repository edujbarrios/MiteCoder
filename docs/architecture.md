# Architecture

## Repository boundaries

MiteCoder uses a small layered monorepo:

```text
frontend (TypeScript) ──HTTP──┐
                              ├──> backend (Python application core)
cli (Python adapter) ─────────┘
```

`backend/` owns domain behavior and infrastructure abstractions. `cli/` translates command-line
arguments into backend calls, while `frontend/` communicates only through the localhost HTTP API.
The backend does not import either outer adapter in application code. Its minimal `__main__`
compatibility shim delegates to the CLI solely to preserve `python -m mitecoder`. Architecture tests
enforce this dependency rule, the absence of the legacy `src/` layout, and the separation between
TypeScript sources and generated browser assets.

## Agent composition

The CLI composes a `Workspace`, retrieval strategy, `ContextBuilder`, inference backend, tool
registry, `BudgetManager`, and metrics collector by dependency injection. In Edge ML terms, the
SLM is only the local policy component; retrieval, tools, state transitions, verification, and
resource accounting form the rest of the deployed intelligent system. The state machine
retrieves once, requests one strict JSON action per inference call, validates it, dispatches a
registered command, records a bounded observation, and repeats. Core code contains no HTTP
service dependency and no global services. Network access is isolated to the explicit
`download-model` setup command; inference and agent execution do not invoke it.

The model cannot submit a shell command. `RunTestsTool` maps an index to an operator-configured
command, uses `shell=False`, and rejects a `command` argument. Following a mutation, every
configured check must pass before the state machine can report verified completion.
`ApplyPatchTool` validates every header path, runs `git apply --check`, and only then applies the
diff.
