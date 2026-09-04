<!-- capsule-v2 -->
# Error-recovery service wipe — how does the manager guarantee clean-slate reinitialization after an error?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** What exactly does recoverFromError reset, and how is it kept re-entrant?

## Nuke services, keep the singleton; guard with a boolean latch
**Path/Symbol:** `src/services/code-index/manager.ts:recoverFromError` (:276-300); per-workspace singleton map :19/:53-68.
**Signature:** `static getInstance(context, workspacePath?): CodeIndexManager | undefined`; `recoverFromError(): Promise<void>`.
**Data Shape:** instances keyed by workspace fsPath; `_isRecoveringFromError: boolean` guards concurrent recovery.

### Decisive source
```ts
this._isRecoveringFromError = true
try {
  this._stateManager.setSystemState("Standby", "")
} catch (error) { /* log but CONTINUE */ }
finally {
  this._configManager = undefined; this._serviceFactory = undefined
  this._orchestrator = undefined; this._searchService = undefined
  this._isRecoveringFromError = false
}
```

**Flow:** recovery clears state to Standby (best-effort) and ALWAYS nulls the four service fields in `finally` — even if the state write threw — so the next `initialize()` rebuilds config→factory→orchestrator→search from scratch. `startIndexing()` on an Error-state manager routes through recovery then RETURNS, delegating the restart to the caller's re-init check. Enablement gating: feature-global toggle AND a per-workspace-folder key (`codeIndexWorkspaceEnabled:<folderUri>`, default auto-enable true) checked BEFORE creating expensive services.
**Invariant:** never partially recreate — validation failure inside `_recreateServices` (embedder validateConfiguration fails ⇒ Error state + throw) leaves the OLD services dead rather than half-new; the manager is "not initialized" until everything succeeds.
**Probe:** `src/services/code-index/__tests__/manager.spec.ts` ("recoverFromError" describe :448+, "should continue recovery even if setSystemState throws" :611, workspace-enabled gating :646+).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "CodeIndexManager recoverFromError _recreateServices _isRecoveringFromError", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt finally-block service nulling + boolean recovery latch + per-folder enablement keys. Adapt singleton scope to your host's window/workspace model. Omit vscode folder-URI resolution details.
