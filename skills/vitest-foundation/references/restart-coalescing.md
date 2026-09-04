<!-- capsule-v2 -->
# Watch-mode restart coalescing — how do overlapping server restarts (chokidar fires several change events per config edit) drain without overlapping or reporting to half-initialized reporters?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How does a config-change restart avoid the overlap crash class where a restart begins while another is still re-creating servers?

## Queued-restart drain loop
**Path/Symbol:** `packages/vitest/src/node/core.ts:Vitest._restart` (270–284) + `_restartNow` (286–302) + epoch guard `restartsCount` used by `scheduleRerun` (1421–1482).
**Signature:** `private _restart(reason?: string): Promise<void>`; `private async _restartNow(reason?: string)`; `private async scheduleRerun(triggerId: string): Promise<void>`.
**Data Shape:** `_restartPromise?: Promise<void>` is the in-flight marker; `_restartQueued: boolean` records "another restart was requested while draining". `restartsCount` increments in `_setRootConfig` and acts as a generation/epoch token for stale watcher callbacks.

### Decisive source
```ts
// Restarts must not overlap: chokidar regularly delivers several change
// events for one edit, and a restart that starts while another is still
// re-creating the servers reports `onServerRestart` to reporters that were
// re-instantiated but not yet initialized.
private _restart(reason?: string): Promise<void> {
  if (this._restartPromise) {
    this._restartQueued = true
    return this._restartPromise
  }
  this._restartPromise = (async () => {
    do {
      this._restartQueued = false
      await this._restartNow(reason)
    } while (this._restartQueued)
  })().finally(() => { this._restartPromise = undefined })
  return this._restartPromise
}
```
And the stale-callback guard inside `scheduleRerun`:
```ts
const currentCount = this.restartsCount   // captured before awaiting
clearTimeout(this._rerunTimer)
await this.cancelPromise
await this.runningPromise
...
// server restarted
if (this.restartsCount !== currentCount) { return }
```

**Flow:** first change event starts the drain (`_restartNow`: notify listeners → report `onServerRestart` → `close()` → reset browser port → resolveConfig → `_start`) → concurrent requests during the drain only set `_restartQueued = true` and share the same promise → after each pass, the loop repeats once if anything was queued → watchers that awaited across a completed restart see `restartsCount` changed and bail instead of rerunning against torn-down state.

**Invariant:** (1) at most one restart pipeline runs at a time — never two overlapping `resolveConfig`/server constructions; (2) every request received DURING a drain is honored exactly once by the trailing loop iteration (no lost restart); (3) callbacks that captured an old `restartsCount` are no-ops after a restart. The comment names the concrete failure it prevents: reporting to reporters that were re-instantiated but not yet initialized ("Cannot read properties of undefined (reading 'logger')").

**Probe:** `test/e2e/test/watch/restart-coalescing.test.ts` (:9–29) — fires `Promise.all([restart('config'), restart('config'), restart('config')])` and asserts stderr has no "Cannot read properties" AND the restarted instance still works (`rerunFiles()` prints RERUN).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "_restart _restartNow restartsCount scheduleRerun", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.vitest.src.node.core.Vitest._restart / ._restartNow / .scheduleRerun
```

## Verdict
Adopt the queued-drain coalescing pattern verbatim for any watch/reload loop driven by chatty FS events, plus the epoch-counter guard for async callbacks captured before an await. Adapt the reason strings and what "re-create servers" means to the host. Omit Vite's own `server.restart` hijack wiring (`this.vite.restart = ...`, core.ts:333–335) unless the host embeds a Vite-style dev server.
