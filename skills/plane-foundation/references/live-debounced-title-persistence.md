<!-- capsule-v2 -->
# Abortable debounced title persistence — how do you debounce per-document field writes without losing the last edit or leaking observers?

**Source:** plane AGPL-3.0-only `preview@e056bbf9eb6b511cdc0a5823b1bd6922e561a485`; Codebase Memory `plane`. **Question:** A CRDT document's title changes on every keystroke — what debounce/abort/cleanup machinery guarantees the final value reaches the API exactly once, even when the document unloads mid-flight?

## Debounce → abort → flush lifecycle
**Path/Symbol:** `apps/live/src/extensions/title-sync.ts:TitleSyncExtension` (:30–181), `title-update/title-update-manager.ts:TitleUpdateManager` (:17–96), `title-update/debounce.ts:DebounceManager` (:48–283), abort-aware transport in `services/page/core.service.ts:updatePageProperties` (:67–116).
**Signature:** `scheduleUpdate(title: string): void`; `forceSave(): Promise<void>`; `cancel(): void`; `DebounceManager.schedule(func, ...args): void` / `.flush(func): Promise<void>` / `.cancel(): void`.
**Data Shape:** Per-document state: `titleObservers: Map<docName, observer>`, `titleUpdateManagers: Map<docName, TitleUpdateManager>`, `titleObserverData: Map<docName, {parentId?, userId, workspaceSlug, instance}>` (side-Map instead of closures to prevent memory leaks); DebounceState `{lastArgs, timerId, lastCallTime, lastExecutionTime, inProgress, abortController}`.

### Decisive source
```ts
private async performFunction(func, time): Promise<void> {
  const currentArgs = [...this.state.lastArgs];
  await this.abortOngoingOperation();               // kill superseded in-flight save (20ms settle + force reset)
  this.state.inProgress = true;
  this.state.abortController = new AbortController();
  try {
    const execArgs = [...currentArgs, this.state.abortController.signal]; // signal appended
    await func(...execArgs);
    if (this.state.lastArgs && this.arraysEqual(this.state.lastArgs, currentArgs)) {
      this.state.lastArgs = null;                   // success only clears args that are still current
    } else if (this.state.lastArgs && !this.state.timerId) { /* newer args arrived: ensure retry timer */ }
  } catch (error) {
    if (error instanceof Error && error.name === "AbortError") { /* silent: newer run owns it */ }
    else if (!this.state.timerId && this.state.lastArgs) { /* schedule retry */ }
  } finally { this.state.inProgress = false; this.state.abortController = null; }
}
// unload path
async beforeUnloadDocument({ documentName }) {
  const updateManager = this.titleUpdateManagers.get(documentName);
  if (updateManager) { await updateManager.forceSave(); this.titleUpdateManagers.delete(documentName); }
}
```

**Flow:** Yjs `document.getXmlFragment("title").observeDeep(observer)` after load (with a one-time migration merge when the `title` field is empty — fetch page name, `TiptapTransformer.toYdoc(json, "title", ...)`, `document.merge`) → each change extracts text and calls `manager.scheduleUpdate(title)` → DebounceManager trailing-edge timer (default wait 5000 ms) with max-wait semantics via `lastCallTime` → on fire: abort any in-flight save, start a fresh AbortController whose signal is APPENDED to the call args → `updatePageProperties` races the axios PATCH against an abort-listener promise and removes the listener in `finally` → success clears lastArgs only if unchanged since; AbortError is swallowed; other errors re-arm the retry timer → `beforeUnloadDocument` forces a flush and deletes the manager; `afterUnloadDocument` does `unobserveDeep` + deletes all three maps (manager cancel as belt-and-suspenders). Title changes also broadcast a realtime `property_updated` event to a parent page when one exists.
**Invariant:** The latest title is never lost: every keystroke refreshes `lastArgs` before any timer logic, a successful save clears them only under an equality check, and unload flushes synchronously. Superseded saves are aborted (AbortError = silence), failed saves retry once per timer cycle, and observers/data maps are always torn down to prevent per-document leaks.
**Probe:** No dedicated upstream test. Deterministic pins: debounce.ts contains `execArgs.push(this.state.abortController.signal)`, `error.name === "AbortError"`, and the 20 ms settle in `abortOngoingOperation`; title-sync.ts contains `unobserveDeep(observer)` and `await updateManager.forceSave()`; core.service.ts contains `Promise.race([this.patch(...), abortPromise])`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "plane", query: "debounce title update manager abort schedule", limit: 5 });
```
Observed at pin: rank-1..3 = DebounceManager.abortOngoingOperation/:199–212, .schedule/:68–101, TitleUpdateManager.scheduleUpdate.

## Verdict
Adopt the args-refresh-before-timer debounce, abort-superseded-writes with silent AbortError, equality-gated arg clearing, flush-on-unload, and the side-Map observer registry; adapt the wait period and what "field" means; omit Plane's parent-page realtime fan-out unless your host has an equivalent tree. Coverage caveat: whole-file reads @ pin; no upstream tests cover these three files.
