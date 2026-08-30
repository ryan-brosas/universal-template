<!-- capsule-v2 -->
# Stable topological presentation order — how does a shuffled graph render dependency-first and deterministically?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I topologically order a task DAG for display so results are identical regardless of input order, even with cycles present?

## orderTaskGraph — Kahn's with stable tie-breaks + cycle tail
**Path/Symbol:** `packages/protocol/src/graph.ts` (`orderTaskGraph`, `compareStableTasks`) (:77–122).
**Signature:** `export function orderTaskGraph(tasks: readonly FactoryTask[]): FactoryTask[]`.
**Data Shape:** in-degree map over deduped in-set dependencies; children adjacency; ready list kept sorted after EVERY mutation.

### Decisive source
```ts
let ready = tasks.filter(task => remainingDependencies.get(task.id) === 0).toSorted(compareStableTasks)
const ordered: FactoryTask[] = []
const seen = new Set<FactoryTaskId>()
while (ready.length > 0) {
    const task = ready.shift()
    if (task === undefined || seen.has(task.id)) continue
    ordered.push(task); seen.add(task.id)
    for (const child of (children.get(task.id) ?? []).toSorted(compareStableTasks)) {
      const remaining = (remainingDependencies.get(child.id) ?? 1) - 1
      remainingDependencies.set(child.id, remaining)
      if (remaining === 0) { ready.push(child); ready = ready.toSorted(compareStableTasks) }
    }
}
return [...ordered, ...tasks.filter(task => !seen.has(task.id)).toSorted(compareStableTasks)]
```

**Flow:** count remaining deps per node → seed roots sorted → repeatedly pop the smallest-key ready node → decrement children → re-sort the ready pool each time a child unlocks → append any never-seen nodes (cycle members / dangling deps) at the TAIL, still stable-sorted.
**Invariant:** Determinism under input shuffle comes from re-sorting the frontier after every unlock (not just seeding), with `createdAt` then numeric-aware identifier as total-order tie-break; cycles cannot hang the traversal — they surface as the unseen tail instead.
**Probe:** `packages/protocol/tests/graph.spec.ts` "orders shuffled task nodes from roots through parallel branches to their join" (`[join,right,root,left]` in → `[root,left,right,join]` out). Deterministic from repo root: `grep -c 'toSorted(compareStableTasks)' packages/protocol/src/graph.ts` = 4.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "orderTaskGraph", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt re-sort-on-unlock Kahn's with the cycle-tail fallback. Adapt the comparator to host identity fields. Omit nothing else — pure function ports verbatim.
