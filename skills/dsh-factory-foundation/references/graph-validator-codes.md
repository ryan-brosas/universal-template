<!-- capsule-v2 -->
# Graph validator — which structural violations make a document uncommittable?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** What must a dependency-graph store check before accepting any write, and how are cycles found cheaply?

## validateTaskGraph — seven machine-coded issues
**Path/Symbol:** `packages/protocol/src/graph.ts` (`validateTaskGraph`) (:8–60); codes in `packages/protocol/src/types.ts` `FactoryGraphIssue` (:451–455).
**Signature:** `export function validateTaskGraph(document: FactoryDocument): FactoryGraphIssue[]` — pure, non-mutating; returns `{ code, message, taskId? }[]`.
**Data Shape:** codes: `missing-dependency | self-dependency | cycle | cross-project | finalizer-dependency | duplicate-inbox | flow-membership`.

### Decisive source
```ts
const color = new Map<FactoryTaskId, 0 | 1 | 2>()
const visit = (id: FactoryTaskId): void => {
    const state = color.get(id) ?? 0
    if (state === 2) return
    if (state === 1) {
      issues.push({ code: 'cycle', taskId: id, message: `dependency cycle reaches ${...}` })
      return
    }
    color.set(id, 1)
    for (const dependency of tasks.get(id)?.dependencyIds ?? []) if (tasks.has(dependency)) visit(dependency)
    color.set(id, 2)
}
```

**Flow:** inbox uniqueness per project → flow membership consistency both directions (flow lists task AND task.flowId agrees) → per-task edge checks (missing id, self-edge, cross-project edge, ordinary task depending on a finalizer) → white/grey/black DFS for cycles. The SQLite store runs this on every mutation draft BEFORE schema-parse; any issue rejects the whole transaction with all messages joined.
**Invariant:** Validation is PURE (no repair, no partial accept) and edges only traverse EXISTING tasks (`if (tasks.has(dependency))`) so missing deps don't crash the DFS — the missing-dependency code covers them instead. Ordinary→finalizer edges are invalid because finalizers are sinks by definition.
**Probe:** `packages/protocol/tests/graph.spec.ts` "reports cycles, invalid finalizer edges, missing nodes, and cross-project edges" (asserts codes arrayContaining cycle/finalizer-dependency/cross-project/missing-dependency) + `packages/store-sqlite/tests/store.spec.ts` "rolls back an invalid graph without advancing the revision" (self-dep rejected `/depends on itself/`, revision stays 0). Deterministic from repo root: `grep -c 'duplicate-inbox' packages/protocol/src/graph.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "validateTaskGraph", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified live: rank-1 `validateTaskGraph Function packages/protocol/src/graph.ts 8-60`.)

## Verdict
Adopt the pure-validator-before-write pattern with the exact seven codes and tri-color DFS. Adapt code vocabulary to host domain. Omit nothing — the whole function ports as-is.
