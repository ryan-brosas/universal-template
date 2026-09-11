<!-- capsule-v2 -->
# Bridge fault injection — one-shot API faults and a debug handle for exercising recovery paths

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you make rare failure modes (poll 404, zombie WS close, register blips) reproducible on demand without shipping test scaffolding to users?

## Path/Symbol
**Path/Symbol:** `src/bridge/bridgeDebug.ts` — whole file: `BridgeFault` shape (:22-36), handle registry (:54-68), `injectBridgeFault` (:70-75), `wrapApiForFaultInjection` (:84-135); consumer wiring in `src/bridge/replBridge.ts` (:327-331 api wrap, :982-1006 debug handle registration, :1349 debugFireClose slot) + `/bridge-kick` invocation.
**Signature:** `wrapApiForFaultInjection(api: BridgeApiClient): BridgeApiClient`; `injectBridgeFault({method, kind: 'fatal'|'transient', status, errorType?, count})`.
**Data Shape:** module-level `debugHandle` + `faultQueue` — deliberate singletons ("one bridge per REPL process; the slash command has no other way to reach into initBridgeCore's closures").

### Decisive source
```ts
// Real failure modes this targets (BQ 2026-03-12, 7-day window):
//   poll 404 not_found_error   — 147K sessions/week, dead onEnvironmentLost gate
//   ws_closed 1002/1006        —  22K sessions/week, zombie poll after close
//   register transient failure —  residual: network blips during doReconnect
...
// Fatal errors go through handleErrorStatus → BridgeFatalError. Transient
// errors surface as plain axios rejections (5xx / network). Recovery code
// distinguishes the two: fatal → teardown, transient → retry/backoff.
```

**Flow:** ant-only wrap (`process.env.USER_TYPE === 'ant' ? wrap : rawApi` — zero cost externally). Each wrapped method consumes a matching queued fault (count decremented; removed at 0) and throws the SPECIFIED error class: 'fatal' constructs BridgeFatalError (flows through the same handleErrorStatus semantics), 'transient' throws a plain Error mimicking an axios rejection with NO `.status`. The handle exposes fireClose(code) (invokes the transport's permanent-close body directly — the real callback is buried two closures deep), forceReconnect, wakePollLoop (so injected poll faults land immediately instead of up to 10min later), and describe() for debug-log greps. Teardown clears the slot.

**Invariant:** (1) The fatal/transient distinction must be reproduced at the ERROR-TYPE level, not by status fields on plain errors — recovery code branches on instanceof. (2) Faults are one-shot counted queues, not toggles: a "next 2 polls fail then recover" scenario is expressible exactly. (3) fireClose must bypass the stale-transport guard in setOnClose but reuse the hoisted close BODY — that's why the body lives at initBridgeCore scope (`handleTransportPermanentClose`). (4) Registration/clear is lifecycle-paired with bridge init/teardown so no stale handle leaks across reconnects.

**Probe:** coverage caveat — no upstream unit tests (the module IS test infrastructure). Deterministic pins: `grep -n "147K sessions/week" src/bridge/bridgeDebug.ts` (:9); `grep -n "fatal → teardown, transient" src/bridge/bridgeDebug.ts` (:28-30); `grep -n "zero overhead in external builds" src/bridge/bridgeDebug.ts` (:82); graph resolves `locoagent.src.bridge.bridgeDebug.wrapApiForFaultInjection` :84-135 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "wrapApiForFaultInjection injectBridgeFault registerBridgeDebugHandle BridgeFatalError transient", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the pattern wholesale when a state machine's recovery paths are production-critical but rarely exercised. Adapt fault vocabulary to your client interface; omit if your app has no privileged-user tier (gate it out instead of deleting).
