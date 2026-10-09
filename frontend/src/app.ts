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

interface ElementMap {
  "active-tab": HTMLDivElement;
  "agent-panel": HTMLElement;
  "agent-state": HTMLSpanElement;
  "agent-toggle": HTMLButtonElement;
  "clear-console": HTMLButtonElement;
  commands: HTMLDivElement;
  console: HTMLDivElement;
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
  "new-task": HTMLButtonElement;
  "open-project": HTMLButtonElement;
  "parent-folder": HTMLButtonElement;
  "profile-value": HTMLElement;
  "project-name": HTMLSpanElement;
  "prompt-history": HTMLSelectElement;
  "refresh-button": HTMLButtonElement;
  "run-button": HTMLButtonElement;
  "ram-value": HTMLElement;
  "save-button": HTMLButtonElement;
  "select-folder": HTMLButtonElement;
  "task-input": HTMLTextAreaElement;
  "task-count": HTMLElement;
  "threads-value": HTMLElement;
}

const state: { activePath: string | null; dirty: boolean; files: FileEntry[]; prompts: string[] } = {
  activePath: null,
  dirty: false,
  files: [],
  prompts: [],
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
    py: "PY", ts: "TS", json: "{}", yaml: "Y", yml: "Y", md: "#", toml: "T",
  };
  return icons[extension] ?? "·";
}

async function loadProject(): Promise<void> {
  const project = await api<Project>("/api/project");
  $("project-name").textContent = project.name;
  $("project-name").title = project.root;
  $("model-name").textContent = project.model;
  $("profile-value").textContent = project.profile;
  $("threads-value").textContent = `${project.threads} threads`;
  $("ram-value").textContent = `${project.max_ram_mb} MB`;
  $("context-value").textContent = `${project.context_length} tokens`;
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

async function openProject(): Promise<void> {
  if (state.dirty && !confirm("Discard unsaved changes and open another project?")) return;
  $("folder-dialog").showModal();
  try {
    await browseFolder($("project-name").title);
  } catch (error) { $("folder-dialog").close(); $("console").innerHTML = `<span class="bad">${escapeText(errorMessage(error))}</span>`; }
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
    $("console").textContent = `Opened local codebase: ${path}`;
  } catch (error) { $("console").innerHTML = `<span class="bad">${escapeText(errorMessage(error))}</span>`; }
}

function rememberPrompt(task: string): void {
  state.prompts = [task, ...state.prompts.filter((item) => item !== task)].slice(0, 12);
  localStorage.setItem("mitecoder-prompts", JSON.stringify(state.prompts));
  renderPromptHistory();
}

function renderPromptHistory(): void {
  const options = state.prompts.map((item) => new Option(item.slice(0, 70), item));
  $("prompt-history").replaceChildren(new Option("Previous prompts", ""), ...options);
}

function restorePromptHistory(): void {
  try {
    const stored = JSON.parse(localStorage.getItem("mitecoder-prompts") ?? "[]") as unknown;
    if (Array.isArray(stored)) {
      state.prompts = stored.filter((item): item is string => typeof item === "string").slice(0, 12);
    }
  } catch {
    state.prompts = [];
  }
  renderPromptHistory();
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

function printResult(result: AgentResult): void {
  const success = result.status === "COMPLETED" && result.verification_passed === true;
  const answered = result.status === "COMPLETED" && result.reason === "answered";
  $("console").innerHTML = `<span class="${success || answered ? "ok" : "bad"}">${success ? "✓ VERIFIED" : answered ? "ANSWER" : "✕ " + result.status}</span>\n\n` +
    `<span class="key">Summary</span>  ${escapeText(result.summary)}\n` +
    `<span class="key">Reason</span>   ${escapeText(result.reason)}\n` +
    `<span class="key">Steps</span>    ${result.steps}\n` +
    `<span class="key">Tokens</span>   ${result.input_tokens} in · ${result.output_tokens} out\n` +
    `<span class="key">Time</span>     ${Number(result.wall_seconds).toFixed(2)}s\n` +
    `<span class="key">Artifacts</span> ${escapeText(result.artifacts || "none")}`;
  $("agent-state").textContent = success ? "Verified" : answered ? "Answered" : "Needs review";
  $("agent-state").className = `agent-state ${success || answered ? "success" : "failure"}`;
}

function escapeText(value: unknown): string {
  const entities: Record<string, string> = {
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  };
  return String(value).replace(/[&<>"']/g, (char) => entities[char] ?? char);
}

async function runAgent(): Promise<void> {
  const task = $("task-input").value.trim();
  if (!task) { $("task-input").focus(); return; }
  if (state.dirty) await saveFile();
  rememberPrompt(task);
  $("run-button").disabled = true;
  $("agent-state").textContent = "Running";
  $("agent-state").className = "agent-state running";
  $("console").textContent = "Loading the local model and running the agent…";
  try {
    const result = await api<AgentResult>("/api/run", { method: "POST", body: JSON.stringify({ task }) });
    printResult(result);
    await refreshTree();
    if (state.activePath) await openFile(state.activePath);
  } catch (error) {
    $("console").innerHTML = `<span class="bad">${escapeText(errorMessage(error))}</span>`;
    $("agent-state").textContent = "Failed";
    $("agent-state").className = "agent-state failure";
  } finally { $("run-button").disabled = false; }
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
$("close-folder").addEventListener("click", () => $("folder-dialog").close());
$("parent-folder").addEventListener("click", () => browseFolder($("parent-folder").dataset.path));
$("select-folder").addEventListener("click", selectFolder);
$("run-button").addEventListener("click", runAgent);
$("agent-toggle").addEventListener("click", () => {
  const open = $("agent-panel").classList.toggle("open");
  $("agent-toggle").setAttribute("aria-expanded", String(open));
});
$("new-task").addEventListener("click", () => { $("task-input").value = ""; updateTaskCount(); $("task-input").focus(); });
$("task-input").addEventListener("input", updateTaskCount);
document.querySelectorAll<HTMLButtonElement>("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => {
    $("task-input").value = button.dataset.prompt ?? "";
    updateTaskCount();
    $("task-input").focus();
  });
});
$("prompt-history").addEventListener("change", () => {
  const selected = $("prompt-history").value;
  if (selected) {
    $("task-input").value = selected;
    updateTaskCount();
  }
});
$("clear-console").addEventListener("click", () => { $("console").innerHTML = '<div class="console-placeholder">Agent output will appear here.</div>'; });
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
restorePromptHistory();
updateTaskCount();
loadProject().catch((error: unknown) => { $("console").textContent = errorMessage(error); });
