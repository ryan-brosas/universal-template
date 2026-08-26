<!-- capsule-v2 -->
# LongStandingScope — how does one peer-death event cancel every present AND future waiter, without sharing a broken stack?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** When a long-lived object dies (page closed/crashed), how do all operations parked on it lose at once — including ones that start racing *after* death — while each loser still gets its own usable stack trace?

## Terminate vs close; late joiners resolved immediately; safeRace defaults instead of rejecting
**Path/Symbol:** `packages/isomorphic/manualPromise.ts:LongStandingScope` (`reject` 63-68, `close` 70-75, `_race` 95-111, `safeRace` 89-93), `cloneError` (126-131); owner example `packages/playwright-core/src/server/page.ts` (`openScope = new LongStandingScope()` :177, `_didDisconnect` 300-308).
**Signature:** `reject(error): void`; `close(error): void`; `race<T>(promise | promises): Promise<T>`; `safeRace<T>(promise, defaultValue?): Promise<T | undefined>`; static `raceMultiple(scopes, promise)`.
**Data Shape:** `_terminateError?`, `_closeError?`, `_terminatePromises: Map<ManualPromise<Error>, string[]>` (one entry per in-flight racer, holding that racer's captured stack frames); `_isClosed` latch.

### Decisive source
```ts
private async _race(promises: Promise<any>[], safe: boolean, defaultValue?: any): Promise<any> {
    const terminatePromise = new ManualPromise<Error>();
    const frames = (new Error().stack || '').split('\n');
    if (this._terminateError)
      terminatePromise.resolve(this._terminateError);
    if (this._closeError)
      terminatePromise.resolve(cloneError(this._closeError, frames));
    this._terminatePromises.set(terminatePromise, frames);
    try {
      return await Promise.race([
        terminatePromise.then(e => safe ? defaultValue : Promise.reject(e)),
        ...promises
      ]);
    } finally {
      this._terminatePromises.delete(terminatePromise);
    }
}
```

**Flow:** every racer registers a fresh `ManualPromise` plus its own stack frames BEFORE awaiting; `reject()` resolves every registered promise with the SAME Error object (terminal, e.g. crash — identity shared so `===` checks work); `close()` resolves each with a per-racer CLONE carrying name/message but the racer's captured frames (graceful close — stacks point at the racing call site). A racer joining after closure resolves synchronously from the stored error — no missed-wakeup window exists. `safeRace` maps the scope error to a default value instead of a rejection, for teardown paths where losing must not mask an outer result. Ownership at page level: `Page.openScope` is created once (:177); `Page._didDisconnect(error: TargetClosedError)` disposes frameManager/screencast/overlay/highlight THEN `openScope.close(error)` (:300-308), guarded by `isClosed()` re-entry check.
**Invariant:** Registration must happen before the await (the map entry IS the wakeup channel); `raceMultiple([a,b], p)` lets any single scope kill the wait — used by Frame retry loops to wake on either page-close or frame-detach; the finally-block deregistration keeps the map from growing across a long-lived scope's lifetime.
**Probe:** repository-owned test pinning observable behavior: `tests/library/page-event-crash.spec.ts` family (actions after close reject promptly) — execution BLOCKED standing in this lane: checkout is read-only with no `node_modules` (exact existence check performed), so Playwright's suite cannot run here; deterministic evidence = byte-exact read of manualPromise.ts:57-132 and page.ts:177,300-308 at pin HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", name_pattern: ".*LongStandingScope.*", detail: "ids", limit: 10 });
```
(executed live → exactly one node: `playwright.packages.isomorphic.manualPromise.LongStandingScope`; consumers located via search_code `openScope = new LongStandingScope` → page.ts:177, Worker:995.)

## Verdict
Adopt the two-flavor termination model (shared-error reject for hard death, cloned-per-racer close for graceful shutdown) and the register-before-await late-joiner guarantee as portable contracts. Adapt ownership placement (Playwright hangs the scope off Page/Frame; your host may hang it off session/connection objects) and error cloning to your stack discipline. Omit `signalToPromise` unless you bridge AbortSignals into scope races. Caveat: no dedicated upstream unit test file for LongStandingScope at this pin — behavior is pinned indirectly through library tests and direct source reads.
