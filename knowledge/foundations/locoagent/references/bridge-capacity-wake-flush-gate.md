<!-- capsule-v2 -->
# Capacity-wake + FlushGate — how do at-capacity sleeps and write gates stay race-free?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How does a poll loop sleep while "at capacity" yet wake instantly on shutdown/capacity-change, and how do message writes queue during a history flush without reordering?

## Path/Symbol
**Path/Symbol:** `src/bridge/capacityWake.ts` — `createCapacityWake` (:28-56, whole file); `src/bridge/flushGate.ts` — `FlushGate<T>` (:16-71, whole file).
**Signature:** `createCapacityWake(outerSignal) → {signal(): {signal, cleanup}, wake()}`; `FlushGate` methods `start()/end(): T[]/enqueue(...items): boolean/drop(): number/deactivate()`.
**Data Shape:** mutable `wakeController: AbortController` — wake() aborts it then **replaces it**; per-sleep merged controller with two `{once:true}` listeners.

### Decisive source
```ts
function signal(): CapacitySignal {
  const merged = new AbortController()
  const abort = (): void => merged.abort()
  if (outerSignal.aborted || wakeController.signal.aborted) {
    merged.abort(); return { signal: merged.signal, cleanup: () => {} }
  }
  outerSignal.addEventListener('abort', abort, { once: true })
  const capSig = wakeController.signal
  capSig.addEventListener('abort', abort, { once: true })
  return { signal: merged.signal, cleanup: () => {
    outerSignal.removeEventListener('abort', abort)
    capSig.removeEventListener('abort', abort) } }
}
```

**Flow:** poll loop's empty-work branch captures `cap = capacityWake.signal()` BEFORE the async work (heartbeat HTTP call), sleeps on the merged signal, then always `cap.cleanup()` — capturing before the await is what catches "session ended during the heartbeat request". wake() aborts-and-replaces so the NEXT sleep arms a fresh controller. FlushGate lifecycle: `start()` → enqueue returns true (queued) → `end()` returns queued items for drain → three distinct endings: `drop()` (permanent close, discard), `deactivate()` (transport REPLACEMENT — new transport's flush drains them), plain end (normal drain).

**Invariant:** (1) Capture the capacity signal before any await inside the loop iteration; after is a lost wakeup. (2) cleanup must run on every path or listeners accumulate (once-listeners don't save you — they're keyed to abort, not to sleep completion). (3) drop-vs-deactivate is the semantic hinge: dropping on transport swap loses live writes; deactivating on permanent close resurrects them into a dead buffer. replBridge calls `flushGate.deactivate()` in onWorkReceived (swap preserves pending) but `flushGate.drop()` in handleTransportPermanentClose (terminal discards). (4) The pre-aborted fast path returns noop cleanup — callers can unconditionally call cleanup.

**Probe:** coverage caveat — no upstream unit tests. Deterministic pins: `grep -n "previously duplicated byte-for-byte" src/bridge/capacityWake.ts` (:8); `grep -n "transport replacement" src/bridge/flushGate.ts` (:13-14); `grep -n "Clear the active flag without dropping" src/bridge/flushGate.ts` (:65); graph resolves all five `FlushGate.*` methods :20-70 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createCapacityWake CapacitySignal FlushGate enqueue deactivate drop", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt both whole — they are ~130 lines total and eliminate the two classic poll-loop bugs (lost wakeups, flush/live interleaving). Porting trap: calling wake() without replacing the controller permanently welds the loop to an already-aborted signal.
