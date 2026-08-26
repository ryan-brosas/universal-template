<!-- capsule-v2 -->
# Waiter failure race — how does waitForEvent lose to crash/close/timeout without leaking listeners?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** When a user waits for an event that may never come, how do timeout, page crash, and page close become clean typed errors — with every listener and timer removed on every exit path?

## One Waiter races target event vs registered failures; __waitInfo__ streams phases
**Path/Symbol:** `packages/playwright-core/src/client/waiter.ts:Waiter` (constructor 37-47, `waitForEvent` 73-76, `rejectOnEvent` 78-81, `rejectOnTimeout` 83-98, `waitForPromise` 114-130, `log` 132-135) + consumer `client/page.ts:_waitForEvent` (504-519).
**Signature:** `rejectOnTimeout({ timeout, signal }: TimeoutOptions, timeoutMessage: string)`; `rejectOnEvent<T>(emitter, event, error | () => Error, predicate?)`; `waitForPromise<T>(promise, dispose?): Promise<T>`.
**Data Shape:** `_failures: Promise<any>[]`; `_dispose: (() => void)[]`; `_logs: string[]`; `_waitId` GUID; wire side-channel `__waitInfo__ { waitId, phase: 'before'|'log'|'after', event?, message?, error? }`.

### Decisive source
```ts
async waitForPromise<T>(promise: Promise<T>, dispose?: () => void): Promise<T> {
    try {
      if (this._immediateError)
        throw this._immediateError;
      const result = await Promise.race([promise, ...this._failures]);
      if (dispose)
        dispose();
      return result;
    } catch (e) {
      if (dispose)
        dispose();
      this._error = e.message;
      this.dispose();                       // removes every registered listener/timer
      rewriteErrorMessage(e, e.message + formatLogRecording(this._logs));
      throw e;
    }
}
```

**Flow:** constructor sends `phase:'before'` wait-info (fire-and-forget; the server NEVER replies — `sendMessageToServer` special-cases `__waitInfo__` to return before registering a callback). Callers register failure promises: crash → `new Error('Page crashed')`, close → `() => this._closeErrorWithReason()` (lazy so the close reason is current), timeout → TimeoutError with message, AbortSignal → AbortError. `waitForEvent` races target-vs-failures inside the saved zone; on ANY settle the per-promise dispose runs, and on failure the whole Waiter disposes itself and appends the log recording (`==== logs ====` banner) to the error message. Page's `_waitForEvent` shows the composition: timeoutOptions → waiter.rejectOnTimeout → rejectOnEvent(crash) unless waiting for crash → rejectOnEvent(close) unless waiting for close → waitForEvent.
**Invariant:** The desired event is NEVER auto-disposed by another failure's dispose (each registration keeps its own dispose thunk); `rejectImmediately` must throw BEFORE racing (`throwIfImmediatelyRejected` / checked first in `waitForPromise`) for pre-aborted signals; wait-info is strictly fire-and-forget — losing it must never affect the wait.
**Probe:** `grep -c "__waitInfo__" packages/playwright-core/src/client/connection.ts` → `4`; `grep -c "phase: 'before'" packages/playwright-core/src/client/waiter.ts` → `1`; `grep -c "formatLogRecording" packages/playwright-core/src/client/waiter.ts` → `2` (def + call); `grep -c "rejectImmediately" packages/playwright-core/src/client/waiter.ts` → `2` (def + immediate-check call); `grep -c "_savedZone" packages/playwright-core/src/client/waiter.ts` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "Waiter rejectOnTimeout", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI: `client.waiter.Waiter.rejectOnTimeout ... waiter.ts 83-98`.)

## Verdict
Adopt the failure-race shape (target promise vs lazily-created typed failures), per-registration dispose thunks, log-recording-on-failure, and structured wait-info streaming. Adapt which sibling events count as failures (crash/close are browser-domain) and your trace-side channel for wait-info. Omit the inspector/debugger hooks. Direct behavior pinned by `tests/library/page-event-crash.spec.ts` ("should throw on any action after page crashes", line 49 — asserts 'crashed'/'has been closed' errors) and `tests/library/browsercontext-events.spec.ts` line 20 (@smoke waitForEvent happy path).
