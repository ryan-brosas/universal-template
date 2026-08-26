<!-- capsule-v2 -->
# Extension handler timeout budget — how do you bound untrusted async handlers without leaking timers or stalling process exit?

**Source:** oh-my-pi (MIT) `main@2b66ee69f249`; Codebase Memory `oh-my-pi`. **Question:** What is the full timeout ladder for extension event handlers, and why is a naive Promise.race with Bun.sleep wrong?

## Connected graph-selected seam
**Path/Symbol:** `packages/coding-agent/src/extensibility/extensions/runner.ts` — caps :86-121 (`EXTENSION_HANDLER_TIMEOUT_MS = 30_000`, `SESSION_SHUTDOWN_HANDLER_TIMEOUT_MS = 2_000`, `handlerTimeoutForEvent`); pausable race `raceHandlerWithTimeout` :242-317; dispatch `#runHandlerWithTimeout` :1249-1332; fail-closed gate `emitToolCall` :1455-1496; concurrent shutdown emit :1342-1355.
**Signature:** `raceHandlerWithTimeout(work: (handlerSignal, budget) => T, timeoutMs, signal?): Promise<T | TIMEOUT | ABORTED>` — sentinel symbols, never throws.
**Data Shape:** budget = `{ pause(): void; resume(): void }`; handler signal = `AbortSignal.any([outerSignal, timeoutController.signal])`; tool_call timeout override via settings key `extensionHandlers.toolCallTimeoutMs` normalized by `normalizeHandlerTimeout`.

### Decisive source
```ts
// issue #3948 review: Bun.sleep(timeoutMs).then(...) leaves an UNCANCELLABLE timer registered
// with the event loop; every successful handler race leaks a timer that keeps the process alive
// until the deadline fires — up to 30s, stalling non-interactive CLI exit. setTimeout returns
// a handle we can clearTimeout on the winning branch:
const expire = () => { if (settled) return; settled = true; clearTimer();
	timeoutController.abort(new DOMException(`Handler timed out after ${timeoutMs}ms`, "TimeoutError"));
	resolveInterrupt(EXTENSION_HANDLER_TIMEOUT); };
const armTimer = () => { if (settled || pauseDepth > 0) return;
	activeSince = performance.now(); timer = setTimeout(expire, Math.max(0, remainingMs)); };
pause:  () => { ...; remainingMs = Math.max(0, remainingMs - (performance.now() - activeSince)); clearTimer(); if (remainingMs <= 0) expire(); },
resume: () => { if (settled || pauseDepth === 0) return; pauseDepth--; if (pauseDepth === 0) armTimer(); },
// after the race returns EXTENSION_HANDLER_TIMEOUT, drain one microtask so an already-settled
await Promise.race([workPromise.then(() => undefined, () => undefined), Bun.sleep(0)]);
```
**Flow:** pre-aborted? return ABORTED -> arm timer -> run work with merged signal + budget -> dialog UI calls budget.pause() while waiting on the HUMAN -> win/timeout/abort settles exactly once -> on TIMEOUT: abort controller, emitError, return onFailure("timeout") which for tool_call is `{ block: true, reason }` (fail-closed: "an unresponsive extension MUST NOT be treated as silent consent to run the tool", #3948).
**Invariant:** (1) timer always cleared on settle — no exit-stall leak; (2) user-facing dialogs pause the budget but inherit the handler signal (`attachHandlerSignal` uses AbortSignal.any), so a timed-out handler cancels its own pending dialog; (3) session_shutdown handlers get the dedicated 2s cap AND run concurrently via Promise.all because teardown is fire-and-forget (#2600: hung IPC must not hold Ctrl+C hostage); (4) dispatch catches everything into handlerFailure — handler errors are reported through onError, never rethrown into the event loop.
**Probe:** anchors at pin: grep "SESSION_SHUTDOWN_HANDLER_TIMEOUT_MS = 2_000" runner.ts; grep "EXTENSION_HANDLER_TIMEOUT_MS = 30_000" runner.ts; test seam `testSetExtensionHandlerTimeoutMs` / `testSetSessionShutdownHandlerTimeoutMs` exist for tests (:93-115).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "raceHandlerWithTimeout", limit: 5 });
```

## Verdict
Adopt: clearTimeout-on-win race with pausable budget, sentinel outcomes, per-event cap table, concurrent fire-and-forget teardown, fail-closed pre-execution gates. Adapt: your settings key names; oh-my-pi folds elapsed wall time only across pause windows. Omit: Bun.sleep microtask-drain detail can become `Promise.resolve()` tick on non-Bun hosts.