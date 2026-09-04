<!-- capsule-v2 -->
# Bridge teardown ordering — result-before-archive-before-close within a 2s cleanup budget

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you flush final events, release server resources, and clear crash state when the whole cleanup gets 2 seconds?

## Path/Symbol
**Path/Symbol:** `src/bridge/remoteBridgeCore.ts` — teardown budget docstring (:658-663), ordering (:664-745: cancelAll → clearTimeout → drop gate → reportState idle → fire-and-forget result → archive(≤1500ms,cap2000) with ONE 401 retry sharing the same budget → close LAST); `src/bridge/replBridge.ts` — `doTeardownImpl` (:1550-1668): duplicate-call latch (:1552-1560), seq capture before close (:1582-1593, "close() is sync and does NOT invoke onClose"), perpetual local-only variant (:1595-1616), stopWork+archive parallel (:1631-1649), deregister then pointer-clear (:1654-1663).
**Signature:** both register via `registerCleanup(teardown)` AND expose explicit `teardown()` (which unregisters first to avoid double-run).
**Data Shape:** `teardown_archive_timeout_ms` default 1500, schema-capped 2000 — "a higher timeout just lies to axios since forceExit kills the socket regardless".

### Decisive source
```ts
// Fire the result message before archive — transport.write() only awaits
// enqueue (SerialBatchEventUploader resolves once buffered, drain is
// async). Archiving before close() gives the uploader's drain loop a
// window (typical archive ≈ 100-500ms) to POST the result without an
// explicit sleep. close() sets closed=true which interrupts drain at the
// next while-check, so close-before-archive drops the result.
transport.reportState('idle')
void transport.write(makeResultMessage(sessionId))
...
// Capture the live transport's seq BEFORE close() — ... Without this,
// getSSESequenceNum() after teardown returns the stale lastTransportSequenceNum
```

**Flow:** latch prevents double-teardown (cleanup registry + explicit handle call race). Order: kill timers/loops → capture live SSE seq (close() never fires onClose) → [perpetual: STOP HERE — no result, no stopWork, no close; lease TTL returns work to pending server-side] → result write enqueued → stopWork(force=true) ∥ archiveSession run in PARALLEL under Promise.all (gracefulShutdown races at 2s) → transport.close() AFTER archive so the uploader drains during archive latency → deregister env → clear pointer. Archive failure taxonomy maps status→BQ categorical (`ok|skipped_no_token|network_error|server_4xx|server_5xx`) with ECONNABORTED distinguished as timeout.

**Invariant:** (1) The three-step result→archive→close order is load-bearing in BOTH cores; reordering loses the final event. (2) Timeouts inside teardown must fit the SHUTDOWN budget, not request-safety budgets — anything >2000ms is fiction. (3) Perpetual teardown is deliberately local-only; signaling the server there kills session continuity that reconnectSession depends on. (4) Explicit teardown must unregister from the cleanup registry first or the registry fires it again mid-flight.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "close-before-archive drops the result" src/bridge/remoteBridgeCore.ts` (:676); `grep -n "does NOT invoke onClose" src/bridge/replBridge.ts` (:1583-1584); `grep -n "LOCAL-ONLY" src/bridge/replBridge.ts` (:1596); graph resolves `locoagent.src.bridge.remoteBridgeCore.initEnvLessBridgeCore` :140-887 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "teardown makeResultMessage archiveSession registerCleanup perpetual doTeardownImpl", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the ordered ladder + budget arithmetic for any resource teardown racing a process-exit deadline. Adapt the archival endpoint; keep the parallel-stop/archive and close-last semantics verbatim.
