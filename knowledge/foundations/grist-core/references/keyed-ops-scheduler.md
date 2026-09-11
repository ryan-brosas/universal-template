<!-- capsule-v2 -->
# KeyedOps — how do you coalesce, delay, retry, and shut down per-key background work?

**Source:** grist-core MIT `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the state machine for "do this eventually, once, per resource key" that survives rapid re-signals, failures, and shutdown ordering?

## changed/operating set scheduler with retry backoff and expedite-on-close
**Path/Symbol:** `app/common/KeyedOps.ts:KeyedOps` (whole file, 245L): `addOperation` (51–54), `_schedule` (131–151), `_update` (181–226), `expediteOperations` (74–82), `stopOperations` (87–90), `wait` (97–105).
**Signature:** `constructor(_op: (key: string) => Promise<void>, _options: { delayBeforeOperationMs?, minDelayBetweenOperationsMs?, retry?, logError?, scheduleFromFirstAdd? })`; `addOperation(key)`, `wait(logRepeat?)`, `expediteOperations()`.
**Data Shape:** three keyed collections — `_operations: Map<string, {timeout?, promise?, failures, callbacks}>` (live status), `_history: Map<string, {lastStart?}>` (rate-limit memory, grows unbounded), `_changed: Set<string>` (needs work), `_operating: Set<string>` (in flight); `_stopped: boolean`.

### Decisive source
```ts
private async _doOp(key: string) {
  if (this._stopped) { throw new Error("operations forcibly stopped"); }
  return this._op(key);
}
// Primitive slow-down on retries.
ticks *= 1 + Math.min(5, status.failures);        // delay ×(failures+1), capped ×6
...
status.promise = this._doOp(key).then(() => {
  status.failures = 0;  /* notify callbacks */
}).catch((err) => {
  status.failures++;
  if (this._options.retry && !this._stopped) { this._changed.add(key); }   // re-arm
  if (this._options.logError) this._options.logError(key, status.failures, err);
  ...
}).then(() => {
  this._operating.delete(key); delete status.promise;
  if (this._changed.has(key)) { this._schedule(key); }      // run again if re-signaled mid-flight
  else if (status.failures === 0 && !status.timeout) this._operations.delete(key); // GC entry
});
```

**Flow:** `addOperation` marks `_changed` + schedules a timer → timer fires (`_update`) ⇒ skip if nothing changed or already in flight; else move key changed→operating, record `lastStart`, run op → success clears failures; failure increments and (if `retry`) re-marks `_changed` so the final `.then` reschedules with multiplied delay → a signal arriving WHILE the op runs simply leaves `_changed` set, guaranteeing one more pass after completion (no lost updates, no overlapping runs). Shutdown: `expediteOperations()` zeroes both delays and reschedules every pending timer to now; `stopOperations()` sets `_stopped` so in-flight ops throw on their next internal check and nothing re-arms; `wait()` loops expedite-and-await until both sets drain.
**Invariant:** at most ONE execution of `_op(key)` can be in flight per key, ever; a call during an execution is deferred-not-dropped; retries are unbounded when enabled but each failure lengthens the next delay up to 6× base; `minDelayBetweenOperationsMs` is measured from last START (history survives entry GC) so hot keys can't spin; callbacks fire exactly once per operation with the error on failure — used by callers to await specific keys (`expediteOperationAndWait`).
**Probe:** no dedicated KeyedOps unit test file exists (coverage caveat: behavior is pinned indirectly through its two production consumers' suites — `test/server/lib/DocSnapshots.ts` pruner scheduling tests :11–85 and `test/server/lib/HostedStorageManager.ts` close/wait flows). Direct assertions live in those files' setup around `pruner.wait()`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "KeyedOps addOperation expediteOperations", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the default primitive for per-entity flush/prune/save work: it answers debouncing, single-flight, min-interval pacing, capped retry backoff, and deterministic shutdown in one dependency-free class. Adapt option defaults and history bounding (grist accepts unbounded `_history`) to host. Omit the callback-notification machinery if you only need fire-and-forget — but keep it if callers must await a specific key's quiescence.
