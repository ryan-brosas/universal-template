<!-- capsule-v2 -->
# Mutation-boundary domain — how do remote mutations fail loud and keep every derived status true?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How should a durable document's mutation API validate ownership and recompute derived state so no caller can corrupt it?

## expectTask/expectProject/expectOwnedRun + deriveFlows
**Path/Symbol:** `packages/domain/src/mutations.ts` (`expectTask`, `expectProject`, `deriveFlows`) (:23–46) + `packages/domain/src/index.ts` (`commit`, `enqueue`, `pause`, `cancel`, `retry` transitions) (:643–941).
**Signature:** `function expectTask(document: FactoryDocument, id: FactoryTaskId): FactoryTask` (throws); `function deriveFlows(document: FactoryDocument, now: string): void`.
**Data Shape:** every `@Remote` mutation funnels through `commit(request, (document, now) => ...)` which threads ONE shared ISO `now` through the whole mutation; activity ledger entries are appended bounded (`activityLimit`, oldest spliced).

### Decisive source
```ts
/** Find a task or fail at the mutation boundary. */
export function expectTask(document: FactoryDocument, id: FactoryTaskId): FactoryTask {
  const task = document.tasks.find(candidate => candidate.id === id)
  if (task === undefined) throw new Error(`Factory task ${id} does not exist`)
  return task
}

/** Recompute every affected flow after task changes. */
export function deriveFlows(document: FactoryDocument, now: string): void {
  const tasks = new Map(document.tasks.map(task => [task.id, task]))
  for (const flow of document.flows) {
    const next = deriveFlowStatus(flow.taskIds.flatMap(id => tasks.get(id) ?? []))
    if (flow.status !== next) { flow.status = next; flow.updatedAt = now }
  }
}
```

**Flow:** Remote call → boundary lookups that THROW on missing ids → lifecycle guards (e.g. `enqueue`: paused+activeRun→waiting / paused recurring→scheduled / draft|failed|cancelled→queued with failure/output/activeRunId cleared / else throw "cannot be queued from") → mutate fields → `deriveFlows` recomputes EVERY flow from member tasks → bounded `activity()` append. Run-scoped mutations additionally pass `expectOwnedRun` (throws "owned by another process" on foreign processId).
**Invariant:** No silent defaults at the boundary — a missing entity is a thrown error, never an undefined-skip; and after ANY task change every flow status is recomputed from scratch (never incrementally patched), so derived status can't drift from the tasks.
**Probe:** `packages/domain/tests/domain.spec.ts` "groups explicit standalone tasks and starts delayed stages atomically" + `packages/protocol/tests/graph.spec.ts` "derives Scheduled flows..." (flow status derives to scheduled from a single scheduled member). Deterministic from repo root: `grep -c 'expectOwnedRun' packages/domain/src/index.ts` = 5.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "deriveFlowStatus", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified live via sibling query pattern: name-exact Function nodes rank-1 line-exact.)

## Verdict
Adopt throw-loud boundary lookups + full-recompute derive + shared-timestamp mutations. Adapt the transition table to host states. Omit the Typert @Remote decorator transport (platform plumbing).
