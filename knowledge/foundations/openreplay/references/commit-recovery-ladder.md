<!-- capsule-v2 -->
# Commit-failure recovery ladder — how does a ~30 ms commit loop survive a dead worker and an idle session?

**Source:** OpenReplay AGPL-3.0 (tracker MIT) `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** Where do batches go when the ticker fires, and what happens if the post fails?

## App._nCommit three-path dispatch + keepalive + restart ladder
**Path/Symbol:** `tracker/tracker/src/main/app/index.ts:_nCommit` (:947–1007), `commit` (:1027–1033), `send` urgent path (:938–940), `emptyBatchCounter` (:277).
**Signature:** `private _nCommit(): void`; invoked by the 30 ms Ticker via `ticker.attach(() => this.commit())` (constructor :352).
**Data Shape:** `this.messages: Array<Message>`; every batch is prefixed `unshift(Timestamp(timestamp()), TabData(tabId))`; keepalive counter `emptyBatchCounter < 1000`.

### Decisive source
```ts
if (!this.messages.length) {
  if (this.emptyBatchCounter < 1000) { this.emptyBatchCounter++; return }
  this.emptyBatchCounter = 0                        // ~every 30s of silence:
  this.worker?.postMessage([Timestamp(this.timestamp()), TabData(...)])  // keepalive
  return
}
try {
  requestIdleCb(() => {
    this.messages.unshift(Timestamp(this.timestamp()), TabData(this.session.getTabId()))
    this.worker?.postMessage(this.messages)
    this.commitCallbacks.forEach((cb) => cb(this.messages))
    this.messages.length = 0
  })
} catch (e) {
  this._debug('worker_commit', e)
  this.stop(true)                       // kill the worker outright…
  setTimeout(() => { void this.start() }, 500)   // …and self-heal with a fresh session start
}
```

**Flow:** `commit()` dispatches on context: socketMode → prefix + hand to commitCallbacks (assist transport owns delivery); insideIframe → `proto.iframeBatch` posted to the parent window so frames share ONE batch stream and index space; normal → idle-callback post to the worker. An empty queue silently counts ticks; after 1000 (~30 s at the 30 ms ticker) it posts a Timestamp+TabData-only batch so the backend session never times out from inactivity. If posting throws, recovery is not retry-in-place: full stop(worker=true) then a delayed fresh `start()`.
**Invariant:** Timestamp+TabData ALWAYS lead a batch — replay ordering depends on it. Keepalive is counted in TICKS, not wall time, so throttled background tabs stretch the interval instead of spamming. Commit failure escalates to a whole-instance restart after 500 ms rather than re-posting into a possibly-poisoned worker; `urgent` sends during Active bypass the tick wait (`send(...,urgent)` → immediate `commit()`).
**Probe:** `grep -n 'worker_commit' tracker/tracker/src/main/app/index.ts` → :1001; `grep -n 'void this.start()' …/app/index.ts` → :478, :1004 (verified live at pin). The 1000-tick keepalive counter anchor (:974) is additionally cited by cold-start-dual-buffer.md.
**Direct test:** none for `_nCommit`; adjacent worker-side send loop is pinned by QueueSender.unit.test.ts (18/18 pass executed at pin).

## Get live surrounding code
**Retrieve (executed):**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "_nCommit commit worker postMessage Timestamp TabData keepalive", limit: 6 });
```
→ rank-2 `App._nCommit :947-1007` line-exact (rank-1 was tracker-redux's unrelated worker.postMessage).

## Verdict
Adopt the tick-counted keepalive, always-prefix batch header, and escalate-to-restart failure handling as pure behavior. Adapt the 30 ms tick, 1000-tick ceiling, and 500 ms restart delay to your throughput budget. Omit the iframe/socket alternate paths unless you share batches across windows.
