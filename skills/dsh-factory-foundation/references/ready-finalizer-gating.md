<!-- capsule-v2 -->
# Ready/finalizer readiness — when is a queued node allowed to claim its lane?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do finalizer tasks gate on their flow's ordinary nodes, and how does the ready queue stay stable and fair?

## isTaskReady + priority ranking + stable order
**Path/Symbol:** `packages/protocol/src/graph.ts` (`isTaskReady`, `factoryPriorityRank`, `compareStableTasks`, `readyTasks`) (:62–87).
**Signature:** `export function isTaskReady(task: FactoryTask, tasks: ReadonlyMap<FactoryTaskId, FactoryTask>): boolean`; `export function readyTasks(document): FactoryTask[]`.
**Data Shape:** `TERMINAL = {'succeeded','failed','cancelled'}`; `finalizerPolicy: 'success' | 'always'`; Linear-compatible `priority 0..4` where **0 means none**.

### Decisive source
```ts
export function factoryPriorityRank(priority: FactoryPriority): number {
  return priority === 0 ? 5 : priority
}
...
if (!task.finalizer) return task.dependencyIds.every(id => tasks.get(id)?.status === 'succeeded')
const flowTasks = task.flowId === undefined ? [] : [...tasks.values()].filter(candidate => candidate.flowId === task.flowId && !candidate.finalizer)
if (!flowTasks.every(candidate => TERMINAL.has(candidate.status))) return false
if (task.finalizerPolicy === 'success' && !flowTasks.every(candidate => candidate.status === 'succeeded')) return false
return task.dependencyIds.every(id => TERMINAL.has(tasks.get(id)?.status ?? 'draft'))
```

**Flow:** ordinary nodes need every dependency `succeeded` (strictly, not just terminal) → finalizers need all ordinary flow-siblings TERMINAL, then policy: `'success'` requires ALL succeeded; `'always'` runs even after failures/cancellations (cleanup must happen) → queue sorted by `rank(priority)` where no-priority(0) sorts LAST as 5, tie-broken by createdAt then numeric-aware identifier.
**Invariant:** The asymmetry IS the contract: dependencies demand SUCCESS for ordinary work but only TERMINALITY for finalizers — that's what lets an always-finalizer run after a failed implementation node (direct test pins exactly this). Priority 0→5 mapping means "unset" can never starve explicit priorities.
**Probe:** `packages/protocol/tests/graph.spec.ts` "runs finalizers after ordinary nodes settle and applies success policy" (`always` ready while failed sibling terminal; `publish`/success-policy NOT ready) and "orders ready tasks by Linear priority and leaves no-priority work last" (expected `[urgent, high, none]`). Deterministic from repo root: `grep -c "priority === 0 ? 5 : priority" packages/protocol/src/graph.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "isTaskReady", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt the success-vs-terminal gating asymmetry and the 0→last rank map. Adapt status vocabulary to host lifecycle. Omit nothing else — pure functions port verbatim.
