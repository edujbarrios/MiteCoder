interface FileEntry { path: string; size: number }
interface FolderEntry { name: string; path: string }
interface Project {
  name: string;
  root: string;
  model: string;
  commands: string[];
  profile: string;
  threads: number;
  context_length: number;
  max_ram_mb: number;
}
interface DirectoryListing { path: string; parent: string | null; folders: FolderEntry[] }
interface AgentResult {
  status: string;
  reason: string;
  summary: string;
  verification_passed: boolean | null;
  steps: number;
  input_tokens: number;
  output_tokens: number;
  wall_seconds: number;
  artifacts?: string;
}
interface TerminalResult { command: string; success: boolean; output: string; returncode: number | null }

interface ElementMap {
  "active-tab": HTMLDivElement;
  "agent-panel": HTMLElement;
  "agent-state": HTMLSpanElement;
  "agent-toggle": HTMLButtonElement;
  "chat-attach": HTMLButtonElement;
  "chat-empty": HTMLDivElement;
  "chat-messages": HTMLDivElement;
  "chat-project-name": HTMLSpanElement;
  commands: HTMLDivElement;
  "context-value": HTMLElement;
  "close-folder": HTMLButtonElement;
  "current-folder": HTMLSpanElement;
  "cursor-position": HTMLSpanElement;
  "dirty-state": HTMLSpanElement;
  editor: HTMLTextAreaElement;
  "editor-wrap": HTMLDivElement;
  "empty-editor": HTMLDivElement;
  "file-filter": HTMLInputElement;
  "file-count": HTMLElement;
  "file-tree": HTMLDivElement;
  "folder-dialog": HTMLDialogElement;
  "folder-list": HTMLDivElement;
  "line-numbers": HTMLPreElement;
  "model-name": HTMLSpanElement;
  "new-chat": HTMLButtonElement;
  "open-project": HTMLButtonElement;
  "parent-folder": HTMLButtonElement;
  "profile-value": HTMLElement;
  "project-name": HTMLSpanElement;
  "refresh-button": HTMLButtonElement;
  "run-button": HTMLButtonElement;
  "ram-value": HTMLElement;
  "save-button": HTMLButtonElement;
  "select-folder": HTMLButtonElement;
  "task-input": HTMLTextAreaElement;
  "task-count": HTMLElement;
  "terminal-clear": HTMLButtonElement;
  "terminal-command": HTMLSelectElement;
  "terminal-output": HTMLPreElement;
  "terminal-panel": HTMLElement;
  "terminal-run": HTMLButtonElement;
  "terminal-toggle": HTMLButtonElement;
  "threads-value": HTMLElement;
}

type ChatRole = "user" | "assistant";
type MessageStatus = "pending" | "success" | "failure";
interface ChatTurn { role: ChatRole; text: string }

const state: { activePath: string | null; dirty: boolean; files: FileEntry[]; conversation: ChatTurn[]; commands: string[] } = {
  activePath: null,
  dirty: false,
  files: [],
  conversation: [],
  commands: [],
};

function $<K extends keyof ElementMap>(id: K): ElementMap[K] {
  const element = document.getElementById(id);
  if (!element) throw new Error(`Required UI element is missing: #${id}`);
  return element as ElementMap[K];
}

async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  const body = await response.json() as T & { error?: string };
  if (!response.ok) throw new Error(body.error ?? `Request failed: ${response.status}`);
  return body as T;
}

function iconFor(path: string): string {
  const extension = path.split(".").pop()?.toLowerCase() ?? "";
  const icons: Record<string, string> = {
    c: "C", cpp: "C+", css: "CS", go: "GO", html: "<>", ipynb: "NB", java: "JV",
    js: "JS", jsx: "JX", json: "{}", md: "#", ps1: "PS", py: "PY", rs: "RS",
    sh: "SH", sql: "DB", toml: "T", ts: "TS", tsx: "TX", yaml: "Y", yml: "Y",
  };
  return icons[extension] ?? "·";
}

async function loadProject(): Promise<void> {
  const project = await api<Project>("/api/project");
  $("project-name").textContent = project.name;
  $("project-name").title = project.root;
  $("chat-project-name").textContent = project.name;
  $("chat-project-name").title = project.root;
  $("model-name").textContent = project.model;
  $("profile-value").textContent = project.profile;
  $("threads-value").textContent = `${project.threads} threads`;
  $("ram-value").textContent = `${project.max_ram_mb} MB`;
  $("context-value").textContent = `${project.context_length} tokens`;
  state.commands = project.commands;
  $("terminal-command").replaceChildren(...project.commands.map((command, index) => new Option(command, String(index))));
  $("terminal-run").disabled = project.commands.length === 0;
  $("commands").textContent = project.commands.length ? `Allowed checks: ${project.commands.join(" · ")}` : "No test commands configured";
  await refreshTree();
}

async function browseFolder(path?: string): Promise<void> {
  const data = await api<DirectoryListing>(`/api/directories${path ? `?path=${encodeURIComponent(path)}` : ""}`);
  $("current-folder").textContent = data.path;
  $("current-folder").title = data.path;
  $("folder-dialog").dataset.path = data.path;
  $("parent-folder").disabled = !data.parent;
  $("parent-folder").dataset.path = data.parent || "";
  const rows = data.folders.map((folder) => {
    const button = document.createElement("button");
    button.className = "folder-row";
    button.innerHTML = '<span class="folder-icon">▸</span><span></span>';
    const label = button.lastElementChild;
    if (label) label.textContent = folder.name;
    button.addEventListener("dblclick", () => browseFolder(folder.path));
    button.addEventListener("click", () => browseFolder(folder.path));
    return button;
  });
  $("folder-list").replaceChildren(...rows);
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

function appendMessage(role: ChatRole, text: string, status?: MessageStatus): HTMLElement {
  $("chat-empty").classList.add("hidden");
  const article = document.createElement("article");
  article.className = `message ${role}-message${status ? ` ${status}` : ""}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "assistant" ? "M" : "You";
  avatar.setAttribute("aria-hidden", "true");

  const body = document.createElement("div");
  body.className = "message-body";
  const author = document.createElement("strong");
  author.textContent = role === "assistant" ? "MiteCoder" : "You";
  const content = document.createElement("p");
  content.textContent = text;
  body.append(author, content);
  article.append(avatar, body);
  $("chat-messages").append(article);
  $("chat-messages").scrollTop = $("chat-messages").scrollHeight;
  return article;
}

function resetChat(): void {
  state.conversation = [];
  $("chat-messages").querySelectorAll(".message").forEach((message) => message.remove());
  $("chat-empty").classList.remove("hidden");
  $("agent-state").textContent = "Ready";
  $("agent-state").className = "agent-state idle";
  $("task-input").value = "";
  updateTaskCount();
  $("task-input").focus();
}

function buildAgentTask(task: string): string {
  const recent = state.conversation.slice(-4);
  if (!recent.length) return task;
  const context = recent
    .map((turn) => `${turn.role === "user" ? "User" : "Assistant"}: ${turn.text.slice(0, 700)}`)
    .join("\n");
  return `Recent conversation about this workspace:\n${context}\n\nCurrent user request:\n${task}`;
}

async function openProject(): Promise<void> {
  if (state.dirty && !confirm("Discard unsaved changes and open another project?")) return;
  $("folder-dialog").showModal();
  try {
    await browseFolder($("project-name").title);
  } catch (error) {
    $("folder-dialog").close();
    appendMessage("assistant", errorMessage(error), "failure");
  }
}

async function selectFolder(): Promise<void> {
  const path = $("folder-dialog").dataset.path;
  try {
    await api<Project>("/api/project", { method: "POST", body: JSON.stringify({ path }) });
    state.activePath = null; state.dirty = false; state.files = [];
    $("active-tab").textContent = "No file open";
    $("active-tab").className = "tab empty";
    $("editor-wrap").classList.add("hidden");
    $("empty-editor").classList.remove("hidden");
    $("save-button").disabled = true;
    await loadProject();
    $("folder-dialog").close();
    resetChat();
  } catch (error) {
    appendMessage("assistant", errorMessage(error), "failure");
  }
}

async function refreshTree(): Promise<void> {
  const data = await api<{ files: FileEntry[] }>("/api/tree");
  state.files = data.files;
  $("file-count").textContent = String(state.files.length);
  renderTree();
}

function renderTree(): void {
  const query = $("file-filter").value.trim().toLowerCase();
  const visible = state.files.filter((file) => file.path.toLowerCase().includes(query));
  const tree = $("file-tree");
  tree.replaceChildren(...visible.map((file) => {
    const button = document.createElement("button");
    button.className = `file${file.path === state.activePath ? " active" : ""}`;
    button.title = `${file.path} · ${file.size} bytes`;
    button.innerHTML = `<span class="file-icon">${iconFor(file.path)}</span><span class="file-name"></span>`;
    const label = button.querySelector<HTMLElement>(".file-name");
    if (label) label.textContent = file.path;
    button.addEventListener("click", () => openFile(file.path));
    return button;
  }));
  if (!visible.length) {
    const empty = document.createElement("div");
    empty.className = "console-placeholder";
    empty.textContent = query ? "No matching files" : "No editable files found";
    tree.replaceChildren(empty);
  }
}

async function openFile(path: string): Promise<void> {
  if (state.dirty && !confirm("Discard unsaved changes?")) return;
  const data = await api<{ content: string }>(`/api/file?path=${encodeURIComponent(path)}`);
  state.activePath = path;
  state.dirty = false;
  $("dirty-state").textContent = "Saved";
  $("dirty-state").className = "";
  $("active-tab").textContent = path.split("/").pop() ?? path;
  $("active-tab").classList.remove("empty");
  $("editor").value = data.content;
  $("empty-editor").classList.add("hidden");
  $("editor-wrap").classList.remove("hidden");
  $("save-button").disabled = false;
  updateLines(); updateCursor(); refreshTree();
}

async function saveFile(): Promise<void> {
  if (!state.activePath) return;
  await api<{ saved: boolean }>("/api/file", { method: "PUT", body: JSON.stringify({ path: state.activePath, content: $("editor").value }) });
  state.dirty = false;
  $("dirty-state").textContent = "Saved";
  $("dirty-state").className = "";
  $("active-tab").textContent = state.activePath.split("/").pop() ?? state.activePath;
}

function updateLines(): void {
  const count = $("editor").value.split("\n").length;
  $("line-numbers").textContent = Array.from({ length: count }, (_, i) => i + 1).join("\n");
}

function updateCursor(): void {
  const editor = $("editor");
  const before = editor.value.slice(0, editor.selectionStart).split("\n");
  $("cursor-position").textContent = `Ln ${before.length}, Col ${(before.at(-1) ?? "").length + 1}`;
}

function updateTaskCount(): void {
  const input = $("task-input");
  $("task-count").textContent = `${input.value.length} / ${input.maxLength}`;
}

function insertIndent(event: KeyboardEvent): void {
  if (event.key !== "Tab") return;
  event.preventDefault();
  const editor = $("editor");
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  editor.setRangeText("    ", start, end, "end");
  editor.dispatchEvent(new Event("input", { bubbles: true }));
}

function printResult(result: AgentResult, message: HTMLElement): void {
  const success = result.status === "COMPLETED" && result.verification_passed === true;
  const answered = result.status === "COMPLETED" && result.reason === "answered";
  message.className = `message assistant-message ${success || answered ? "success" : "failure"}`;
  const body = message.querySelector<HTMLElement>(".message-body");
  if (body) {
    const author = document.createElement("strong");
    author.textContent = success ? "MiteCoder · Verified" : answered ? "MiteCoder · Answer" : `MiteCoder · ${result.status}`;
    const summary = document.createElement("p");
    summary.textContent = result.summary;
    const metrics = document.createElement("div");
    metrics.className = "run-metrics";
    metrics.textContent = `${result.steps} steps · ${result.input_tokens} in / ${result.output_tokens} out · ${Number(result.wall_seconds).toFixed(2)}s`;
    const details = document.createElement("p");
    details.className = "message-details";
    details.textContent = `Reason: ${result.reason}${result.artifacts ? ` · Artifacts: ${result.artifacts}` : ""}`;
    body.replaceChildren(author, summary, metrics, details);
  }
  $("agent-state").textContent = success ? "Verified" : answered ? "Answered" : "Needs review";
  $("agent-state").className = `agent-state ${success || answered ? "success" : "failure"}`;
  $("chat-messages").scrollTop = $("chat-messages").scrollHeight;
}

async function runAgent(): Promise<void> {
  const task = $("task-input").value.trim();
  if (!task) { $("task-input").focus(); return; }
  if (state.dirty) await saveFile();
  const agentTask = buildAgentTask(task);
  state.conversation.push({ role: "user", text: task });
  appendMessage("user", task);
  $("task-input").value = "";
  updateTaskCount();
  $("run-button").disabled = true;
  $("agent-state").textContent = "Running";
  $("agent-state").className = "agent-state running";
  const pending = appendMessage("assistant", "Reading the workspace and running the local agent…", "pending");
  try {
    const result = await api<AgentResult>("/api/run", { method: "POST", body: JSON.stringify({ task: agentTask }) });
    printResult(result, pending);
    state.conversation.push({ role: "assistant", text: result.summary });
    await refreshTree();
    if (state.activePath) await openFile(state.activePath);
  } catch (error) {
    pending.className = "message assistant-message failure";
    const content = pending.querySelector("p");
    if (content) content.textContent = errorMessage(error);
    $("agent-state").textContent = "Failed";
    $("agent-state").className = "agent-state failure";
  } finally { $("run-button").disabled = false; }
}

async function runTerminalCommand(): Promise<void> {
  const index = Number($("terminal-command").value);
  if (!Number.isInteger(index) || index < 0 || index >= state.commands.length) return;
  $("terminal-panel").classList.remove("collapsed");
  $("terminal-toggle").textContent = "⌄";
  $("terminal-run").disabled = true;
  $("terminal-output").className = "terminal-output";
  $("terminal-output").textContent = `$ ${state.commands[index]}\nRunning…`;
  try {
    const result = await api<TerminalResult>("/api/terminal", { method: "POST", body: JSON.stringify({ index }) });
    $("terminal-output").className = `terminal-output ${result.success ? "success" : "failure"}`;
    $("terminal-output").textContent = `$ ${result.command}\n${result.output || `(process exited with code ${result.returncode ?? "unknown"})`}`;
    await refreshTree();
    if (state.activePath && !state.dirty) await openFile(state.activePath);
  } catch (error) {
    $("terminal-output").className = "terminal-output failure";
    $("terminal-output").textContent = errorMessage(error);
  } finally {
    $("terminal-run").disabled = state.commands.length === 0;
  }
}

$("editor").addEventListener("input", () => {
  state.dirty = true;
  const path = state.activePath;
  $("active-tab").textContent = `${path?.split("/").pop() ?? "File"} ●`;
  updateLines();
});
$("editor").addEventListener("scroll", () => { $("line-numbers").scrollTop = $("editor").scrollTop; });
$("editor").addEventListener("input", () => {
  $("dirty-state").textContent = "Unsaved changes";
  $("dirty-state").className = "dirty";
});
$("editor").addEventListener("keyup", updateCursor);
$("editor").addEventListener("click", updateCursor);
$("editor").addEventListener("keydown", insertIndent);
$("save-button").addEventListener("click", saveFile);
$("refresh-button").addEventListener("click", refreshTree);
$("file-filter").addEventListener("input", renderTree);
$("open-project").addEventListener("click", openProject);
$("chat-attach").addEventListener("click", openProject);
$("close-folder").addEventListener("click", () => $("folder-dialog").close());
$("parent-folder").addEventListener("click", () => browseFolder($("parent-folder").dataset.path));
$("select-folder").addEventListener("click", selectFolder);
$("run-button").addEventListener("click", runAgent);
$("new-chat").addEventListener("click", resetChat);
$("terminal-run").addEventListener("click", runTerminalCommand);
$("terminal-clear").addEventListener("click", () => {
  $("terminal-output").className = "terminal-output";
  $("terminal-output").textContent = "Select an allowed project command and run it here.";
});
$("terminal-toggle").addEventListener("click", () => {
  const collapsed = $("terminal-panel").classList.toggle("collapsed");
  $("terminal-toggle").textContent = collapsed ? "⌃" : "⌄";
  $("terminal-toggle").title = collapsed ? "Show terminal" : "Hide terminal";
});
$("agent-toggle").addEventListener("click", () => {
  const open = $("agent-panel").classList.toggle("open");
  $("agent-toggle").setAttribute("aria-expanded", String(open));
});
$("task-input").addEventListener("input", updateTaskCount);
$("task-input").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    runAgent();
  }
});
document.querySelectorAll<HTMLButtonElement>("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    $("task-input").value = button.dataset.prompt ?? "";
    updateTaskCount();
    $("task-input").focus();
  });
});
document.addEventListener("keydown", (event) => { if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); saveFile(); } });
document.addEventListener("keydown", (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    event.preventDefault();
    runAgent();
  }
});
window.addEventListener("beforeunload", (event) => {
  if (state.dirty) event.preventDefault();
});
updateTaskCount();
loadProject().catch((error: unknown) => { appendMessage("assistant", errorMessage(error), "failure"); });
