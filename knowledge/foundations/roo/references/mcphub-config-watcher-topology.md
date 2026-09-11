<!-- capsule-v2 -->
# Config file watcher set (global settings + project mcp.json + workspace folders) — which files must be watched, how are events debounced, and what happens when the project config is DELETED?

**Source:** Roo-Code (Roo Code, Inc.) Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** What is the complete watcher topology that keeps live connections in sync with on-disk MCP configs?

## Three watcher families → 500ms debounce → parse-validate-reconcile; deletion = cleanup
**Path/Symbol:** `src/services/mcp/McpHub.ts` (`watchMcpSettingsFile` :510–544 global; `watchProjectMcpFile` :362–405 project incl. delete; `setupWorkspaceFoldersWatcher` :284–296; debounce :301–322; handler :324–360; per-server chokidar watchers :1178–1252).
**Signature:** constructor wires all three synchronously/async (:166–175) with `initializationPromise = Promise.all([initializeGlobalMcpServers, initializeProjectMcpServers])`.
**Data Shape:** global pattern = exact settings filename under its dir; project pattern = `RelativePattern(workspaceFolder, ".roo/mcp.json")`; test-env guard: both watchers skip when `process.env.NODE_ENV === "test"` or `createFileSystemWatcher` is absent.

### Decisive source
```ts
// :395-400 — project-config deletion is a FIRST-CLASS event
this.projectMcpWatcher.onDidDelete(async () => {
    await this.cleanupProjectMcpServers()
    await this.notifyWebviewOfServerChanges()
    vscode.window.showInformationMessage(t("mcp:info.project_config_deleted"))
})
```
```ts
// :349-359 — ENOENT inside the debounced handler mirrors the same cleanup
if (error.code === "ENOENT" && source === "project") {
    await this.cleanupProjectMcpServers()
    ...
}
```

**Flow:** change/create on either file → debounce keyed `"${source}-${filePath}"` at 500ms → read+parse (syntax error = toast + abort; schema error = toast listing paths + abort) → `updateServerConnections(servers, source)` reconcile. Workspace-folder changes re-run project update AND rebuild the project watcher (new folder ⇒ new RelativePattern). Per-server watchPaths/build/index.js chokidar watchers restart individual servers.
**Invariant:** invalid JSON must NEVER tear down running servers — parse/validation failures return before reconcile, keeping last-good state live; deletion handling exists at BOTH the watcher event and the read-race ENOENT path because the file can vanish between event and read. Global watcher has NO delete branch: deleting global settings must not nuke user servers.
**Probe:** deterministic probes:
`grep -n '.roo/mcp.json' src/services/mcp/McpHub.ts` → **1 site** (:379), `grep -c 'onDidDelete' src/services/mcp/McpHub.ts` = **1** (:395), `grep -c 'cleanupProjectMcpServers' src/services/mcp/McpHub.ts` = **3** (:352 ENOENT call, :397 onDidDelete call, :441 def), `grep -cF 'NODE_ENV === "test"' src/services/mcp/McpHub.ts` = **3** (:286 showErrorMessage toast guard, :364 project-watcher guard, :512 global-watcher guard; single-quote the pattern - double-escaped backslash-quote forms match nothing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "watchMcpSettingsFile watchProjectMcpFile debounce", limit: 5 });
// Method rows McpHub.watchMcpSettingsFile 510-544 / watchProjectMcpFile 362-405 resolve in the updateServerConnections/debounce family (total: 389)
```

## Verdict
Adopt the three-family topology with validate-before-reconcile and dual-path delete handling. Adapt patterns/paths to your host's config locations. Omit VSCode-specific toast copy.
