<!-- capsule-v2 -->
# CCR four-uploader composition + delivery acks — how do you wire one uploader kernel into four channels with distinct budgets, and ack inbound events without racing the first frame?

**Source:** locoagent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Given a generic serial batch uploader (see serial-batch-uploader-retry-machine), what per-channel configs, queue bounds, and constructor-ordering does a real worker need — and how do delivery receipts flow?

## Four channels over one kernel; ack wiring in the CONSTRUCTOR
**Path/Symbol:** `src/cli/transports/ccrClient.ts`: fields/:286-292, workerState/:346-357, eventUploader/:359-385, internalEventUploader/:387-408, deliveryUploader/:410-436, received-ack wiring/:438-445, `reportDelivery`/:964-969, `internalEventsPending`/:976-979; status mapping `src/cli/remoteIO.ts`:155-167.
**Signature:** each channel = `new SerialBatchEventUploader<T>({ maxBatchSize, maxBatchBytes, maxQueueSize, send: async batch => {…throw new RetryableError(msg, result.retryAfterMs)}, baseDelayMs: 500, maxDelayMs: 30_000, jitterMs: 500 })`.
**Data Shape:** workerState→`PUT /worker` (via WorkerStateUploader); eventUploader→`POST /worker/events` (public SSE mirror); internalEventUploader→`POST /worker/internal-events` (worker-private transcript); deliveryUploader→`POST /worker/events/delivery` `{updates:[{event_id,status}]}` with statuses `received|processing|processed`.

### Decisive source
```ts
maxBatchSize: 100,
maxBatchBytes: 10 * 1024 * 1024,
// flushStreamEventBuffer() enqueues a full 100ms window of accumulated
// stream_events in one call. A burst of mixed delta types that don't
// fold into a single snapshot could exceed the old cap (50) and deadlock
// on the SerialBatchEventUploader backpressure check. Match
// HybridTransport's bound — high enough to be memory-only.
maxQueueSize: 100_000,
```
```ts
// Ack each received client_event so CCR can track delivery status.
// Wired here (not in initialize()) so the callback is registered the
// moment new CCRClient() returns — remoteIO must be free to call
// transport.connect() immediately after without racing the first
// SSE catch-up frame against an unwired onEventCallback.
transport.setOnEvent((event) => this.reportDelivery(event.event_id, 'received'))
```

**Flow:** outbound lifecycle → remoteIO installs listeners (`setCommandLifecycleListener`, `setSessionStateChangedListener`, `setSessionMetadataChangedListener`) that call reportDelivery/reportState/reportMetadata; inbound SSE frames → onEvent ⇒ 'received' immediately, then command lifecycle started/completed maps to processing/processed (`LIFECYCLE_TO_DELIVERY`). Every send failure throws RetryableError carrying the server's retryAfterMs so the shared kernel honors it (auth taxonomy capsule). UUIDs injected when missing (toClientEvent :754-762) keep retries idempotent.
**Invariant:** Queue bounds are PER CHANNEL and encode the channel's burst shape: public events 100_000 (memory-only bound — the 100ms coalescing window enqueues whole windows at once; a 50-cap DEADLOCKED on backpressure), internal 200, delivery 64/64. The received-ack MUST be wired in the constructor: connect() may fire before initialize() resolves, and early catch-up frames' acks would otherwise be silently dropped. reportDelivery is void/fire-and-forget (`void …enqueue`) — delivery telemetry must never block the event path.
**Probe:** `grep -n "deadlock" src/cli/transports/ccrClient.ts` (`:364` comment), `grep -n "maxQueueSize: 100_000" src/cli/transports/ccrClient.ts` (`:367`), `grep -n "reportDelivery(event.event_id, 'received')" src/cli/transports/ccrClient.ts` (`:444`), `grep -n "started: 'processing'" src/cli/remoteIO.ts` (`:156`). No upstream unit tests — deterministic anchors are the probe tier.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "^(reportDelivery|reportState|reportMetadata)$", limit: 5 });
// ccrClient methods :964-969/:645-658/:661-663 line-exact; bonus cross-plane confirmation:
// replBridgeTransport's thin forwarders :327-332 (executed live pre-write)
```

## Verdict
Adopt the per-channel budget reasoning (burst-shape ⇒ maxQueueSize) and constructor-time ack wiring for any multi-channel writer over a shared queue kernel. Adapt endpoints/status vocab to your API. Omit the delivery channel only if your transport has native acks (WS does — see ws-replay-buffer).
