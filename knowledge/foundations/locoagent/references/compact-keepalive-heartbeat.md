<!-- capsule-v2 -->
# Compact keep-alive heartbeat — how do you stop a 5-10 minute silent compaction from being declared dead by an idle-timeout on a remote bridge?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What liveness signals must a long quiet operation emit, and how are they cleaned up?

## compact-keepalive-heartbeat
**Path/Symbol:** `src/services/compact/compact.ts` (`streamCompactSummary` activity block :1159-1176, `clearInterval` :1393-1395).
**Signature:** `setInterval(cb, 30_000, context.setSDKStatus)` armed only when `isSessionActivityTrackingActive()`; handle stored and cleared in `finally`.
**Data Shape:** two signals per tick: `sendSessionActivitySignal()` (PUT /worker heartbeat) + re-emit `'compacting'` SDK status so the event stream stays active.

### Decisive source
```ts
// Send keep-alive signals during compaction to prevent remote session
// WebSocket idle timeouts from dropping bridge connections. Compaction
// API calls can take 5-10+ seconds, during which no other messages
// flow through the transport — without keep-alives, the server may
// close the WebSocket for inactivity.
// Two signals: (1) PUT /worker heartbeat via sessionActivity, and
// (2) re-emit 'compacting' status so the SDK event stream stays active
// and the server doesn't consider the session stale.
```

**Flow:** arm interval before either transport path → tick every 30s during potentially minutes-long compaction → `finally { clearInterval(activityInterval) }` guarantees teardown across success/fallback/throw. The status setter is passed as a setInterval REST PARAMETER (`setInterval(fn, ms, arg)`) rather than closed over — harmless but notable idiom.
**Invariant:** any operation that can outlast a transport's idle timeout must own its liveness: BOTH protocol-level (heartbeat endpoint) and application-level (status re-emission) signals, because either alone can be insufficient; the timer must be cleared on EVERY exit path or it fires into a torn-down context. Gate arming on feature-detection of remote sessions — local sessions pay nothing.
**Probe:** no upstream test. Deterministic pins: `grep -n "idle timeouts" src/services/compact/compact.ts` → :1160; `grep -n "clearInterval(activityInterval)" src/services/compact/compact.ts` → :1394; `grep -n "30_000" src/services/compact/compact.ts` → :1173.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "sendSessionActivitySignal isSessionActivityTrackingActive compact", limit: 10 });
```

## Verdict
Adopt dual-signal keep-alive with finally-guaranteed teardown for long quiet operations over bridged transports. Adapt signal endpoints/intervals. Coverage caveat: no unit tests upstream.
