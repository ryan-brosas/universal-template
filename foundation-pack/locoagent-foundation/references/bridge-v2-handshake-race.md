<!-- capsule-v2 -->
# Bridge v2 handshake race — generation counters vs null-checks for async transport swaps

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When two async transport constructions can race while the transport slot is null, why does a presence check pick the WRONG winner and how do you fix it?

## Path/Symbol
**Path/Symbol:** `src/bridge/replBridge.ts` — `v2Generation` declaration + race docstring (:543-550), unconditional bump on ANY new transport (:1373-1375), stale-resolution discard (:1394-1414), init-failure epoch release (:1417-1441); sibling pattern in jwtUtils (`generations` map, see bridge-token-refresh-scheduler).
**Signature:** `let v2Generation = 0` — captured as `thisGen` before the async call; compared AFTER resolution.
**Data Shape:** plain module-closure int; bumped by onWorkReceived AND doReconnect.

### Decisive source
```ts
// Bumped on every onWorkReceived. Captured in createV2ReplTransport's .then()
// closure to detect stale resolutions: if two calls race while transport is
// null, both registerWorker() (bumping server epoch), and whichever resolves
// SECOND is the correct one — but the transport !== null check gets this
// backwards (first-to-resolve installs, second discards). The generation
// counter catches it independent of transport state.
...
// onWorkReceived may have fired again while registerWorker() was in flight
// (server re-dispatch with a fresh JWT). ...
if (thisGen !== v2Generation) {
  logForDebugging(`[bridge:repl] CCR v2: discarding stale handshake gen=${thisGen} current=${v2Generation}`)
  t.close()
  return
}
```

**Flow:** work re-dispatch fires onWorkReceived again while the first createV2ReplTransport awaits registerWorker. Both saw transport===null; both registered workers (each bumping the SERVER-side epoch — only the newest is valid). Resolution order is arbitrary: a transport-slot check installs whichever resolves FIRST and closes the second — exactly inverted. The generation check compares the captured int against current: any intervening bump (new dispatch, reconnect) makes the older resolution close itself. Failure path mirrors it: a stale init failure must not stopWork for a newer attempt's live work item.

**Invariant:** (1) Presence checks (`transport !== null`) cannot order ASYNC completions — they encode "someone won", not "the latest won". (2) Every mutation site of the guarded slot bumps the generation unconditionally (even v1 transports invalidate an in-flight v2 handshake). (3) A discarded transport must still be CLOSED — its heartbeat timer would otherwise leak. (4) The same primitive appears twice in this repo (jwtUtils per-session generations) — when you find yourself adding a third, extract it.

**Probe:** coverage caveat — no upstream unit tests for this path. Deterministic pins: `grep -n "whichever resolves" src/bridge/replBridge.ts` (:546-547); `grep -n "discarding stale handshake" src/bridge/replBridge.ts` (:1409-1411); `grep -n "Bump unconditionally" src/bridge/replBridge.ts` (:1373); graph resolves `locoagent.src.bridge.replBridge.startWorkPollLoop` :1851-2398 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "v2Generation discarding stale handshake createV2ReplTransport thisGen", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the capture-bump-compare trio for any cached-async-resource swap (transports, sockets, sessions). Adapt naming; omit nothing — the "second resolver wins" inversion is invisible until production double-dispatch.
