<!-- capsule-v2 -->
# Bridge transport adapters — v1/v2 behind one surface, seq-num carryover, delivery-ACK overwrite

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you confine a v1/v2 protocol choice to the construction site and keep the write/read/auth semantics straight when only one side has sequence numbers?

## Path/Symbol
**Path/Symbol:** `src/bridge/replBridgeTransport.ts` — `ReplBridgeTransport` surface (:23-70), `createV1ReplTransport` (:78-103), `createV2ReplTransport` (:119-370): auth closure vs env-var (:169-181), epoch-mismatch handler (:209-231), received+processed ACK overwrite (:249-252), connect() deferred init (:336-368), close-code synthesis (4090 epoch, 4091 init-fail, 4092 budget-exhausted :309-314).
**Signature:** `createV2ReplTransport({sessionUrl, ingressToken, sessionId, initialSequenceNum?, epoch?, heartbeatIntervalMs?, heartbeatJitterFraction?, outboundOnly?, getAuthToken?}) → Promise<ReplBridgeTransport>`.
**Data Shape:** v2 = SSETransport(reads) + CCRClient(writes/heartbeat/state/delivery); v1 = HybridTransport(WS reads + POST writes). `getLastSequenceNum()` returns 0 on v1 by contract; `droppedBatchCount` returns 0 on v2.

### Decisive source
```ts
// CCRClient's constructor wired sse.setOnEvent → reportDelivery('received').
// ... events stay at 'received' forever, and reconnectSession re-queues
// them on every daemon restart (observed: 21→24→25 phantom prompts as
// "user sent a new message while you were working" system-reminders).
//
// Fix: ACK 'processed' immediately alongside 'received'. The window between
// SSE receipt and transcript-write is narrow ... a crash there loses one
// prompt vs. the observed N-prompt flood on every restart.
sse.setOnEvent(event => {
  ccr.reportDelivery(event.event_id, 'received')
  ccr.reportDelivery(event.event_id, 'processed')
})
```

**Flow:** v1 wraps HybridTransport verbatim; its POSTs are awaited per-write so flush() resolves immediately and reportState/Metadata/Delivery are no-ops. v2: derive SSE URL from http base (`pathname + '/worker/events/stream'`), register worker unless epoch came from /bridge, wire `onEpochMismatch` to close-and-throw (default was process.exit — correct for spawned children, fatal in-process) with close-in-try so the unwind always executes, then return an object whose writes go through SerialBatchEventUploader (writeBatch loops per-message checking `closed`). isConnectedStatus = WRITE-readiness (`ccrInitialized`), deliberately not SSE state. setOnClose maps undefined (budget exhaustion) to synthetic 4092 and stops the heartbeat timer first.

**Invariant:** (1) Auth inversion is the core trap: v1 accepts OAuth (standard refresh flow covers it); v2 REQUIRES the session-bound JWT (register_worker.go validates session_id claim) — passing OAuth to v2 endpoints fails every call. (2) getLastSequenceNum()==0 must be preserved for v1 so replBridge's carryover math no-ops instead of replaying history. (3) onConnect fires when ccr.initialize() resolves, NOT when the SSE stream opens — outbound writes never wait on reads. (4) Delivery-ACK eager-processing trades one lost prompt on crash for N phantom prompts per restart.

**Probe:** coverage caveat — no upstream unit tests for this adapter file. Deterministic pins: `grep -n "phantom prompts" src/bridge/replBridgeTransport.ts` (:242); `grep -n "epoch superseded" src/bridge/replBridgeTransport.ts` (:230); `grep -n "Write-readiness, not read-readiness" src/bridge/replBridgeTransport.ts` (:290); graph resolves `locoagent.src.bridge.replBridgeTransport.createV2ReplTransport` :119-370 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createV2ReplTransport createV1ReplTransport ReplBridgeTransport reportDelivery getLastSequenceNum", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the single-surface adapter pattern wholesale when migrating between stream protocols. Adapt close codes to your telemetry vocabulary; omit outboundOnly if you have no mirror mode. Porting trap: letting the child transport default to process.exit inside a long-lived process.
