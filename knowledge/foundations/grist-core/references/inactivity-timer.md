<!-- capsule-v2 -->
# Keep-Open Inactivity Timer — how do you retire an idle resource on a timer without killing it mid-operation (including infinite user loops)?

**Source:** grist-core Apache-2.0 `main@b83224bbe9c88910dfeb28922df254a26f702f68`; Codebase Memory `grist-core`. **Question:** What is the exact mechanism that schedules auto-shutdown of an idle document, unschedules it when work arrives, and caps how long one pending operation may hold it open?

## Counter-gated ping/enable/disable with disableUntilFinish activity counting
**Path/Symbol:** `app/common/InactivityTimer.ts` — class `InactivityTimer` (:16–115): `ping()` (:57–61), `enable()`/:37–40, `disable()`/:42–47, `setDelay()`/:29–31, `disableUntilFinish(promise)` (:71–86), `_beginActivity`/_endActivity (:88–97), `_onTimeoutTriggered` (:108–113). Consumed by `app/server/lib/ActiveDoc.ts`: field `_inactivityTimer = new InactivityTimer(() => this._onInactive(), Deps.ACTIVEDOC_TIMEOUT * 1000)` (:352–355), `@ActiveDoc.keepDocOpen` decorator (:276–284), constructor arms it immediately (`this._inactivityTimer.enable()`, :535), `addClient` disables (:691–695), `closeDoc` re-enables at zero clients (:1064–1073), `fetchQuery` pings per read (:1407).
**Signature:** `ping(): void` — no-op unless `_counter === 0 && _enabled`; `disableUntilFinish<T>(promise: Promise<T>): Promise<T>`.
**Data Shape:** state = `{_timeout?: NodeJS.Timeout, _counter: number, _enabled: boolean, _delay: number}`; callback fires once then the timer stays off until the next activity.

### Decisive source
```ts
public keepDocOpen(target: ActiveDoc, propertyKey: string, descriptor: PropertyDescriptor) {
  descriptor.value = function(this: ActiveDoc) {
    const result = origFunc.apply(this, arguments);
    this._inactivityTimer.disableUntilFinish(timeoutReached(Deps.KEEP_DOC_OPEN_TIMEOUT_MS, result))
      .catch(() => {});
    return result;
  };
}
// InactivityTimer core:
public ping() {
  if (!this._counter && this._enabled) { this._setTimeout(); }
}
public async disableUntilFinish<T>(promise: Promise<T>): Promise<T> {
  this._beginActivity();            // counter++ AND clearTimeout
  try { return await promise; }
  finally { this._endActivity(); }  // counter-- then ping()
}
private async _onInactive() {
  if (Deps.ACTIVEDOC_TIMEOUT_ACTION === "shutdown") {
    await this.shutdown({ beforeShutdown: async () => { ...vacuum with ENOENT tolerance... } });
  }
}
```

**Flow:** constructor enables the timer BEFORE any client exists ("Schedule shutdown immediately... If not [connected], the ActiveDoc will get cleaned up", :532–535) → first client `disable()`s it; last client `closeDoc` re-enables → every read `ping`s → long operations decorated `keepDocOpen` hold it via `disableUntilFinish`, which clears the pending timeout and re-arms only after the promise settles → timeout fires `_onInactive` → shutdown whose `beforeShutdown` vacuums the SQLite file (ENOENT tolerated for already-deleted docs) → after load completes, the delay is scaled to load time: `closeTimeout = Math.max(loadMs, 1000) * ACTIVEDOC_TIMEOUT` (:3093–3098).
**Invariant:** (1) A doc is NEVER retired while any `keepDocOpen` operation is in flight — but that hold is itself bounded by `KEEP_DOC_OPEN_TIMEOUT_MS` (5 min) so an infinite-loop formula cannot pin the process forever (source comment :232–236 says exactly this). (2) `ping` is inert while `_counter > 0`: activity tracking always wins over idleness. (3) Timeout fires exactly once; re-arming requires explicit new activity.
**Probe:** direct tests `test/common/InactivityTimer.ts`: "if no activity, should trigger when time elapses after ping" (:15), "disableUntilFinish should clear timeout, and set it back after promise resolved" (:22), "should not trigger during async monitoring" (:31), "should support disabling" (:49); integration side: `testKeepOpen()` (:2214) used by `test/server/lib/HostedStorageManager.ts:864,:918`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "grist-core",
  query: "InactivityTimer keepDocOpen disableUntilFinish ping", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-layer design: raw timer primitive (ping/disable/counter), decorator wrapper converting "long op started" into a bounded hold, and lifecycle wiring (arm-at-construction, disarm-on-first-consumer, re-arm-on-zero, delay scaled by observed load cost). Adapt timeouts/delays to host; you can skip the load-time scaling. Omit Electron/dev-vs-prod timeout switching unless you have the same two environments. Note: `KEEP_DOC_OPEN_TIMEOUT_MS` races are acknowledged as untested edge (source TODO :3040–3042).
