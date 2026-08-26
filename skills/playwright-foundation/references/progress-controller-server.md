<!-- capsule-v2 -->
# ProgressController (server) — how does the server turn a deadline into cancellation?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `ext-playwright`. **Question:** On the server side of the pipe, how do I enforce a timeout against an arbitrary async task — including tasks that ignore their own cancellation — and keep nested race calls honest?

## State machine + force-abort promise + AbortController fan-out
**Path/Symbol:** `packages/playwright-core/src/server/progress.ts:ProgressController` (`abort` 66-80, `run` 82-162), `raceUncancellableOperationWithCleanup` (173-185), `isAbortError` (167-169).
**Signature:** `run<T>(task: (progress: Progress) => Promise<T>, timeout?: number): Promise<T>`; `abort(error): Promise<void>`; `progress.race<T>(promise | promises): Promise<T>`; `progress.wait(timeout): Promise<void>` (0 = no-wait here, NOT forever); `raceUncancellableOperationWithCleanup<T>(progress, run, cleanup): Promise<T>`.
**Data Shape:** `_state: 'before' | 'running' | { error } | 'finished'`; `_forceAbortPromise: ManualPromise<any>`; `_controller: AbortController`; `_pendingAbortError?` for aborts arriving before `run`.

### Decisive source
```ts
if (deadline) {
  const timeoutError = new TimeoutError(`Timeout ${timeout}ms exceeded.`);
  timer = setTimeout(() => {
    // TODO: migrate this to "progress.disableTimeout()".
    if (this.metadata.pauseStartTime && !this.metadata.pauseEndTime)
      return;
    if (this._state === 'running') {
      this._state = { error: timeoutError };
      this._forceAbortPromise.reject(timeoutError);
      this._controller.abort(timeoutError);
    }
  }, deadline - monotonicTime());
}
...
race: <T>(promise: Promise<T> | Promise<T>[]) => {
  ...
  const promises = Array.isArray(promise) ? promise : [promise];
  if (!promises.length)
    return Promise.resolve();
  return Promise.race([...promises, this._forceAbortPromise]).finally(() => outerProgress = undefined);
},
```

**Flow:** every server API method runs inside `ProgressController.run`: a monotonic deadline arms a timer whose fire rejects `_forceAbortPromise` AND aborts the AbortController (two cancellation channels: Promise.race for awaited helpers, signal for signal-aware native APIs). `abort()` before `run` parks the error in `_pendingAbortError`, which `run` throws at entry — an early abort is never lost. Task completion flips state to `'finished'`; a late timeout tick checks `_state === 'running'` so a finished task's timer cannot reject anything. `progress.wait(0)` means NO wait (opposite of the usual timeout convention). Under `PW_DETECT_NESTED_PROGRESS`, calling `race()` while another `race()` is on the stack logs both stacks unless `setAllowConcurrentOrNestedRaces(true)` opted in. `isAbortError` treats TimeoutError as abort-family via name check OR the symbol tag. The cleanup helper runs `cleanup(t)` when the raced operation succeeded but the progress had already aborted — for operations that cannot be interrupted mid-flight.
**Invariant:** All racing must go through `progress.race` (which splices in `_forceAbortPromise`) — raw `Promise.race` bypasses cancellation; the pause-window check (`pauseStartTime && !pauseEndTime`) suspends the deadline while a debugger pauses; exactly one winner between finish/error/abort because state transitions are guarded.
**Probe:** `grep -c "_forceAbortPromise" packages/playwright-core/src/server/progress.ts` → `5`; `grep -c "Cannot call race() inside another race()" packages/playwright-core/src/server/progress.ts` → `1`; `grep -c "kAbortErrorSymbol" packages/playwright-core/src/server/progress.ts` → `4`; `grep -c "raceUncancellableOperationWithCleanup" packages/playwright-core/src/server/progress.ts` → `1`; `grep -c "pauseStartTime" packages/playwright-core/src/server/progress.ts` → `1`; `grep -c "_pendingAbortError" packages/playwright-core/src/server/progress.ts` → `5`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-playwright", query: "ProgressController", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI: `server.progress.ProgressController.run ... progress.ts 82-162`.)

## Verdict
Adopt the dual-channel cancellation (race-promise + AbortSignal), pre-run abort parking, finished-guard on late timers, and the uncancellable-op cleanup pattern. Adapt monotonic-clock source and the nested-race detector to your debug tooling. Omit `nullProgress` unless you need no-op server calls. Direct unit coverage of ProgressController is internal-only at this commit (exercised through every server-side timeout path in the library suite); treat the grep pins as commit-scoped contract evidence.
