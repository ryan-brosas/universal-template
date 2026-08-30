<!-- capsule-v2 -->
# Solid ownership tree — how do computations register under owners, and how does disposal unsubscribe O(1)?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** How is the Owner/Listener global pair swapped to scope creation, and what exact bookkeeping makes cleanup correct?

## createComputation + cleanNode: owned-list lifecycle with slot swap-removal
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:createComputation` (:1441-1521), `cleanNode` (:1700-1738), `createRoot` (:150-185), `onCleanup` (:1016-1022).
**Signature:** `function createComputation(fn: EffectFunction<Init|Next, Next>, init: Init, pure: boolean, state: ComputationState = STALE, options?: EffectOptions): Computation`.
**Data Shape:** `Owner { owned: Computation[] | null, cleanups, owner, context }`; `Computation extends Owner { fn, state, sources, sourceSlots, updatedAt, pure, user }`. Globals: `Owner` (creation scope), `Listener` (tracking scope).

### Decisive source
```ts
else if (Owner !== UNOWNED) {
    if (!Owner.owned) Owner.owned = [c];
    else Owner.owned.push(c);
}
...
// cleanNode subscription removal:
while ((node as Computation<any>).sources!.length) {
      const source = (node as Computation<any>).sources!.pop()!,
        index = (node as Computation<any>).sourceSlots!.pop()!,
        obs = source.observers;
      if (obs && obs.length) {
        const n = obs.pop()!,
          s = source.observerSlots!.pop()!;
        if (index < obs.length) {
          n.sourceSlots![s] = index;
          obs[index] = n;
          source.observerSlots![index] = s;
        }
      }
}
```

**Flow:** create → snapshot `owner: Owner`, `context: Owner?.context` → register in `Owner.owned` (skipped for `UNOWNED` roots) → on dispose: recurse `owned` children first, pop every `(source, slot)` pair while swap-removing this node from each source's observer arrays, run `cleanups` in reverse registration order, reset `state = 0`. `cleanNode` runs BEFORE every re-run (`updateComputation`) so conditional dependencies are re-collected fresh — that is what "Repeated signal reads clean up conditional dependencies" (signals.spec :164-196) proves.
**Invariant:** The four parallel arrays (`sources/sourceSlots` on the computation; `observers/observerSlots` on the signal) must stay symmetric or the swap-remove corrupts other observers' slots. Cleanups always run newest-first. A zero-argument root function means UNOWNED (dispose throws in dev). Dev warning: computations created outside a root "will never be disposed".
**Probe:** `grep -c 'if (index < obs.length) {' packages/solid/src/reactive/signal.ts` → `1` (the swap-removal branch). Behavior pinned by signals.spec "Clean an effect" (:482), "Explicit root disposal" (:499), "Failed Root disposal from arguments" (:509).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "cleanNode owned cleanups sources sourceSlots", limit: 10 });
```

## Verdict
Adopt the owner tree + reverse-order cleanups + swap-remove unsubscription verbatim — it is the disposal backbone of every Solid-like system. Adapt globals into async-context storage on servers. Omit `tOwned` transition twins until transitions are ported.
