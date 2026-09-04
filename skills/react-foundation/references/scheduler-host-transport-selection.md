<!-- capsule-v2 -->
# Scheduler host transport selection — which API posts the next work tick, and why not always MessageChannel?

**Source:** facebook/react MIT `main@055705ca01766d2a4379261b05e7990a849bdedc`; Codebase Memory `react`. **Question:** In what order must a port probe host macrotask APIs for the work tick, and how is double-posting prevented?

## setImmediate > MessageChannel > setTimeout(0) with single-flight guard
**Path/Symbol:** `packages/scheduler/src/forks/Scheduler.js:schedulePerformWorkUntilDeadline` binding block (:530–561), `requestHostCallback` (:563–568), local native captures (:96–101), `requestHostTimeout/cancelHostTimeout` (:570–584).
**Signature:** `schedulePerformWorkUntilDeadline: () => void` (chosen once at module load); `requestHostCallback(): void`.
**Data Shape:** Module-level `isMessageLoopRunning: boolean`, `taskTimeoutID: TimeoutID`; one pre-created `MessageChannel` with `port1.onmessage = performWorkUntilDeadline`.

### Decisive source
```js
if (typeof localSetImmediate === 'function') {
  // Node.js and old IE.
  // ... Unlike MessageChannel, it doesn't prevent a Node.js process from exiting.
  // https://github.com/facebook/react/issues/20756
  schedulePerformWorkUntilDeadline = () => {
    localSetImmediate(performWorkUntilDeadline);
  };
} else if (typeof MessageChannel !== 'undefined') {
  // DOM and Worker environments.
  // We prefer MessageChannel because of the 4ms setTimeout clamping.
  const channel = new MessageChannel();
  const port = channel.port2;
  channel.port1.onmessage = performWorkUntilDeadline;
  schedulePerformWorkUntilDeadline = () => {
    port.postMessage(null);
  };
} else {
  // We should only fallback here in non-browser environments.
  schedulePerformWorkUntilDeadline = () => {
    localSetTimeout(performWorkUntilDeadline, 0);
  };
}
```
Single-flight:
```js
function requestHostCallback() {
  if (!isMessageLoopRunning) {
    isMessageLoopRunning = true;
    schedulePerformWorkUntilDeadline();
  }
}
```

**Flow:** first task arrives → requestHostCallback flips the flag and posts once → every queued task drains inside that message → performWorkUntilDeadline clears the flag only when flushWork returns false. Timer-based delayed tasks use the separately captured `localSetTimeout/localClearTimeout` pair (`taskTimeoutID`), never the transport.
**Invariant:** At most one posted-but-unhandled work tick exists; multiple scheduleCallback calls while the loop runs must not post again. Native APIs are captured into locals at module scope (:96–101) so polyfills installed later cannot hijack them. The transport choice is made ONCE at load, not per-post.

**Probe:** `packages/scheduler/src/__tests__/Scheduler-test.js` `'task that finishes before deadline'` (:176–183): scheduling logs exactly `['Post Message']` before firing and `['Message Event', 'Task']` after — one post per drain cycle. The mock runtime's `fireMessageEvent` stands in for MessageChannel delivery (:44–174).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "react", query: "requestHostCallback MessageChannel setImmediate isMessageLoopRunning", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the three-tier probe order with its documented reasons (Node exit hang #20756; 4ms clamp) and the single-flight flag. Adapt to runtimes lacking all three (e.g., queueMicrotask+atimer hybrids) but keep capture-at-load. Omit the IE-era comments. Coverage caveat: parse_partial source read directly at :530–568.
