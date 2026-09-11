<!-- capsule-v2 -->
# Flow status derivation — how does a group's status emerge from its members' lifecycle?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** What is the correct precedence ladder when deriving a flow's single status from heterogeneous task statuses?

## deriveFlowStatus — ordered predicate ladder
**Path/Symbol:** `packages/protocol/src/graph.ts` (`deriveFlowStatus`) (:125–135).
**Signature:** `export function deriveFlowStatus(tasks: readonly FactoryTask[]): FactoryFlowStatus`.
**Data Shape:** flow statuses `draft|scheduled|queued|running|waiting|succeeded|failed|cancelled`; finalizer members are EXEMPT from failure/cancellation contagion and can be cancelled inside an otherwise-succeeded flow.

### Decisive source
```ts
if (tasks.every(task => task.status === 'draft')) return 'draft'
const ordinary = tasks.filter(task => !task.finalizer)
if (ordinary.some(task => task.status === 'failed')) return 'failed'
if (ordinary.some(task => task.status === 'cancelled')) return 'cancelled'
if (tasks.every(task => task.status === 'succeeded' || (task.finalizer && task.status === 'cancelled'))) return 'succeeded'
if (tasks.some(task => task.status === 'waiting' || task.status === 'paused')) return 'waiting'
if (tasks.some(task => ['dispatching', 'running'].includes(task.status))) return 'running'
if (tasks.some(task => task.status === 'scheduled')) return 'scheduled'
return 'queued'
```

**Flow:** all-draft → draft → any ordinary failed → failed → any ordinary cancelled → cancelled → succeeded only if every member succeeded OR is a CANCELLED FINALIZER → waiting (waiting/paused) beats running beats scheduled, else queued.
**Invariant:** Order of the ladder IS the semantics: failure outranks cancellation, both outrank success; a cancelled finalizer never poisons a finished flow (cleanup was cancelled on purpose), but a cancelled ORDINARY node fails the whole flow; human-input states (waiting/paused) outrank execution states so a blocked node is visible even while siblings run. Direct test pins `deriveFlowStatus([failed ordinary, always-finalizer queued, publish queued])` = `'failed'` despite two pending finalizers.
**Probe:** `packages/protocol/tests/graph.spec.ts` "runs finalizers after ordinary nodes settle and applies success policy" (derives 'failed') and "derives Scheduled flows..." (single scheduled member → 'scheduled'). Deterministic from repo root: `grep -c "task.finalizer && task.status === 'cancelled'" packages/protocol/src/graph.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "deriveFlowStatus", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt the ladder verbatim including the cancelled-finalizer exemption. Adapt status names to host lifecycle. Omit nothing — pure function.
