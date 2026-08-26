<!-- capsule-v2 -->
# Retry loop + non-retriable taxonomy — how does a retry loop sleep in backoff yet wake INSTANTLY on page close, and which errors must never be retried?

**Source:** playwright Apache-2.0 `main@d4e1023f6c03a8dced50eb3db88c2217e7c1a86a`; Codebase Memory `playwright`. **Question:** When an action (click/fill/wait) must retry until an element is actionable, how do you bound the backoff sleeps by peer lifetime, and where is the line between "retry" and "throw now"?

## Instant-wake backoff via scope raceMultiple; five-way throw gate
**Path/Symbol:** `packages/playwright-core/src/server/frames.ts:Frame` (`retryWithProgressAndTimeouts` 1157-1183, `isNonRetriableError` 1185-1199); scopes owned at `server/page.ts:177` (`openScope`) and Frame `_detachedScope`.
**Signature:** `retryWithProgressAndTimeouts<R>(progress: Progress, timeouts: number[], action: (progress: Progress, continuePolling: symbol) => Promise<R | symbol>): Promise<R>`; `isNonRetriableError(e: Error): boolean`.
**Data Shape:** `timeouts` is a backoff ladder consumed positionally and clamped to its last element; `action` signals "retry" by returning the per-call `continuePolling` Symbol sentinel (never thrown, so it cannot collide with real values); result type is `R` or the symbol.

### Decisive source
```ts
timeouts = [0, ...timeouts];
let timeoutIndex = 0;
while (true) {
  const timeout = timeouts[Math.min(timeoutIndex++, timeouts.length - 1)];
  if (timeout) {
    // Make sure we react immediately upon page close or frame detach.
    // We need this to show expected/received values in time.
    const actionPromise = new Promise(f => setTimeout(f, timeout));
    await progress.race(LongStandingScope.raceMultiple([
      this._page.openScope,
      this._detachedScope,
    ], actionPromise));
  }
  try {
    const result = await action(progress, continuePolling);
    if (result === continuePolling)
      continue;
    return result as R;
  } catch (e) {
    if (this.isNonRetriableError(e))
      throw e;
    continue;
  }
}
```

```ts
isNonRetriableError(e: Error) {
    if (isAbortError(e))                       // TimeoutError or kAbortErrorSymbol-tagged
      return true;
    if (js.isJavaScriptErrorInEvaluate(e) || isSessionClosedError(e))
      return true;                             // JS error or main connection closed
    if (dom.isNonRecoverableDOMError(e) || isInvalidSelectorError(e))
      return true;                             // DOM/selector fatal
    if (this._isDetached())
      return true;                             // call made on detached frame
    return false;                              // everything else retries
}
```

**Flow:** `[0, ...timeouts]` guarantees the FIRST attempt runs with zero delay; each later gap sleeps through a plain timer that is raced against BOTH the page's openScope and the frame's detachedScope via `LongStandingScope.raceMultiple` — so close/detach kills the sleep instantly instead of waiting out the backoff (comment: needed "to show expected/received values in time"). The sleep also goes through `progress.race`, so timeout/client-cancel preempts it too. Retry decision is a five-clause throw-gate evaluated in strict order: abort-family first (so the controller's deadline wins over any retry), then evaluate-JS errors and session-closed, then non-recoverable DOM / invalid selector, then detached-frame-as-state, and only otherwise continue.
**Invariant:** the loop has NO iteration cap — termination comes exclusively from action success, a non-retriable error, or progress cancellation; therefore every caller MUST run it under a ProgressController timeout. The `continuePolling` sentinel must be compared with `===` (symbol identity), making accidental collision impossible. Ordering matters: checking `isAbortError` before session-closed means a cancelled call reports cancellation, not "closed".
**Probe:** repository-owned behavior pins: `tests/page/page-wait-for-selector.spec.ts` family (wait resolves/rejects across navigation/detach) and the close-race behavior exercised throughout `tests/library/` — full suite execution BLOCKED standing in this lane (read-only checkout, no node_modules); deterministic evidence = byte-exact reads of frames.ts:1157-1199 and page.ts:177,300-308 at pin HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "playwright", name_pattern: ".*retryWithProgressAndTimeouts.*", detail: "ids", limit: 5 });
```
(executed live → exactly one node, frames.ts :1157-1183; companion name_pattern search for `isNonRetriableError` → frames.ts :1185-1199.)

## Verdict
Adopt zero-first-delay ladders, sleeping THROUGH the peer-lifetime scope race, the symbol-sentinel retry signal, and an ordered abort-first throw-gate. Adapt the taxonomy predicates (`isJavaScriptErrorInEvaluate`, `isNonRecoverableDOMError`, …) to your host's error classes — the ORDERING discipline is the portable part. Omit the expected/received screenshot rationale unless your host renders diff output on failure. Pairs with `long-standing-scope-terminate-close` (the wake channel) and `progress-controller-server` (the outer deadline).
