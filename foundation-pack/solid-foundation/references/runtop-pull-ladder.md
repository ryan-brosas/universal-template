<!-- capsule-v2 -->
# Solid runTop pull ladder — how does reading a PENDING memo evaluate ancestors in dependency order without a topological sort?

**Source:** SolidJS solid MIT `main@f47845f9cc16ecbb316aa6560c7161f45af9a3d8`; Codebase Memory `solid` (pass-3 refresh from retired `ext-solid` @ identical pin). **Question:** When a memo is read while only marked PENDING, how does Solid guarantee its upstream chain is fresh first — and each node exactly once?

## runTop + lookUpstream: ancestor walk with ExecCount guard
**Path/Symbol:** `packages/solid/src/reactive/signal.ts:runTop` (:1523-1554) and `lookUpstream` (:1670-1684).
**Signature:** `function runTop(node: Computation<any>)`, `function lookUpstream(node: Computation<any>, ignore?: Computation<any>)` — both module-private.
**Data Shape:** Walks the `owner` linked-list upward collecting stale ancestors; `ExecCount` is a global epoch incremented per `runUpdates`; `updatedAt` stores the last ExecCount at which a computation ran.

### Decisive source
```ts
const ancestors = [node];
while (
    (node = node.owner as Computation<any>) &&
    (!node.updatedAt || node.updatedAt < ExecCount)
  ) {
    if (runningTransition && Transition!.disposed.has(node)) return;
    if (runningTransition ? node.tState : node.state) ancestors.push(node);
}
for (let i = ancestors.length - 1; i >= 0; i--) {
    ...
    if ((runningTransition ? node.tState : node.state) === STALE) {
      updateComputation(node);
    } else if (... === PENDING) {
      const updates = Updates;
      Updates = null;
      runUpdates(() => lookUpstream(node, ancestors[0]), false);
      Updates = updates;
    }
}
```

**Flow:** start at the requested node → walk owners upward while they haven't already run this epoch (`updatedAt < ExecCount`) and are dirty → reverse-iterate so the OLDEST ancestor runs first → STALE nodes re-run via `updateComputation`; PENDING nodes clear their mark by recursively running their own upstream (`lookUpstream`) instead of themselves.
**Invariant:** Topological order without a topo sort: an ancestor always appears before its dependents in the reversed ancestor list, so by the time a memo re-runs, every source it will read is fresh — this is exactly what `test/signals.memo.spec.ts` "propagates in topological order" (:6-49) pins as sequence `b1b2c1`. The `updatedAt < ExecCount` check makes each node run at most once per batch even when reached from multiple paths ("only propagates once with exponential convergence", :80-123). The tricky orderings in "evaluates stale computations before dependees when trackers stay unchanged" (t2c2t1c1, :334-366) fall out of the same walk.
**Probe:** `grep -c 'if (!node.updatedAt || node.updatedAt < ExecCount)' packages/solid/src/reactive/signal.ts` → matches the owner-walk condition; `lookUpstream` recursion guard is `else if (state === PENDING) lookUpstream(source, ignore);`. Behavior pinned by the three memo.spec tests above.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "solid", query: "runTop lookUpstream updatedAt ExecCount", limit: 10 });
```

## Verdict
Adopt the ancestor-walk-with-epoch pattern for lazy pull graphs. Adapt: hosts with eager push scheduling need only the marking half. Omit: the transition-disposed early return unless porting transitions.
