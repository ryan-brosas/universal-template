<!-- capsule-v2 -->
# Refresh coalescing + quiesce lifecycle — how do you keep a polling publisher fresh under bursts without overlapping refreshes or losing the last one?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** what is the concurrency contract for a component that both heartbeats periodically and refreshes on demand?

## Single-flight refresh with trailing-edge re-arm
**Path/Symbol:** `src/topology/participant-directory.ts:ParticipantDirectory.refresh` (:288-302), `scheduleRefresh` (:274-286), `start` (:254-272), `quiesce` (:458-463), `close` (:465-484).
**Signature:** `refresh(): Promise<void>` (callers joining an in-flight refresh receive THE SAME promise); `scheduleRefresh()` coalesces via `#refreshScheduled` flag + `queueMicrotask`; `#refreshAgain` latches requests arriving mid-flight.
**Data Shape:** state flags `#refreshing?: Promise<void>`, `#refreshScheduled`, `#refreshAgain`, `#closed`, `#quiescing`; heartbeat `setInterval(() => void this.refresh().catch(() => undefined), heartbeatMs)` with `.unref()`.

### Decisive source
```ts
async refresh(): Promise<void> {
  if (this.#closed) return;
  if (this.#refreshing) return this.#refreshing;          // join, don't overlap
  const operation = this.#refresh();
  this.#refreshing = operation;
  try {
    await operation;
  } finally {
    if (this.#refreshing === operation) this.#refreshing = undefined;   // identity guard
    if (this.#refreshAgain) { this.#refreshAgain = false; this.scheduleRefresh(); }  // trailing edge
  }
}
```
```ts
// The heartbeat doubles as the recovery path: even when the initial publish
// fails (for example a contended mesh lock at startup), keep retrying so this
// host joins the mesh once the lock clears instead of staying invisible until
// the next restart.
this.#timer = setInterval(() => void this.refresh().catch(() => undefined), this.#heartbeatMs);
```

**Flow:** demand-side callers hit scheduleRefresh (microtask-coalesced — N synchronous requests produce ONE refresh) or await refresh directly (concurrent callers share one operation); if a request lands WHILE refreshing, `#refreshAgain` schedules exactly one more AFTER completion → start() runs one initial refresh whose failure is re-thrown to the caller but does NOT stop the interval → quiesce awaits any in-flight refresh THEN forces a final full pass (publishing capability-stripped records per topology-participant-directory) → close clears the timer first, then drains `#refreshing` so no write outlives the object.
**Invariant:** never two concurrent #refresh bodies (mesh writes stay serialized per directory); a request is never LOST — it either joins the in-flight pass or re-arms one trailing pass; timer callbacks swallow errors (heartbeats must not crash the host) while the initial refresh surfaces its error.
**Probe:** `tests/participant-directory.test.ts:416` ("recovers via heartbeat when the initial publish fails at startup"), teardown ordering pinned by `:149` ("withdraws control capabilities before releasing its live host lease") which drives quiesce→get→mesh assertions through this lifecycle.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "ParticipantDirectory refresh scheduleRefresh quiesce close", limit: 5, fields: ["signature", "name", "file"] });
```
