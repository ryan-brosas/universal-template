<!-- capsule-v2 -->
# Solid signal core — how do signals register observers without duplicate subscriptions and route reads through transition state?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** How does a signal read subscribe a computation exactly once per run while serving the correct value during transitions?

## Signal read path: dual bookkeeping + last-observer fast check
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:readSignal` (:1302-1339).
**Signature:** `export function readSignal(this: SignalState<any> | Memo<any>)` — always `.bind(signal)`-style bound, never called with an explicit receiver.
**Data Shape:** `SignalState` = `{ value, observers: Computation[] | null, observerSlots: number[] | null, comparator? }`; Memo adds `sources/sourceSlots/state/updatedAt/pure/fn`. Parallel index arrays (`observers[i] ↔ observerSlots[i]`) are kept symmetric with each listener's `sources/sourceSlots`.

### Decisive source
```ts
if (Listener) {
    const observers = this.observers;
    if (!observers || observers[observers.length - 1] !== Listener) {
      const sSlot = observers ? observers.length : 0;
      if (!Listener.sources) {
        Listener.sources = [this];
        Listener.sourceSlots = [sSlot];
      } else {
        Listener.sources.push(this);
        Listener.sourceSlots!.push(sSlot);
      }
      if (!observers) {
        this.observers = [Listener];
        this.observerSlots = [Listener.sources.length - 1];
      } else {
        observers.push(Listener);
        this.observerSlots!.push(Listener.sources.length - 1);
      }
    }
}
```

**Flow:** read → if memo has stale `state/tState`, escalate to `updateComputation` or `lookUpstream` first → if a `Listener` is active, append this signal to Listener's `sources` AND append Listener to this signal's `observers` at symmetric indexes (skipped when Listener is already the LAST observer — the common re-read case) → return `tValue` if a running transition has claimed this node, else `value`.
**Invariant:** The subscription is idempotent within one run because of the tail-check `observers[observers.length - 1] !== Listener`; naive "push if not includes" ports are O(n) per read and break nothing but benchmarks; naive unconditional pushes corrupt `observerSlots` symmetry that `cleanNode` relies on for O(1) swap-remove.
**Probe:** `grep -c 'observers[observers.length - 1] !== Listener' packages/solid/src/reactive/signal.ts` → `1`. Behavior pinned by `test/signals.spec.ts` "Repeated signal reads update once per write" (:128-145): reading a signal 1000× inside one effect yields exactly 2 runs total across a write.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "readSignal Listener sources sourceSlots", limit: 10 });
```

## Verdict
Adopt the symmetric two-array subscription model + last-observer fast path for any pull-reactivity port. Adapt the global `Listener` variable into your host's tracking context if you cannot use module globals. Omit the transition `tValue` branch until you port transitions (see scheduler capsule). Direct vitest runner BLOCKED in inspo clone (no node_modules); probes verified byte-exact against source on disk.
