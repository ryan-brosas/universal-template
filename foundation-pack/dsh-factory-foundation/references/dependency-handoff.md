<!-- capsule-v2 -->
# Dependency handoff — how does a downstream task receive its predecessors' receipts bounded?

**Source:** dsh-factory MIT `main@3405edc7`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-dsh-factory`. **Question:** How do I render predecessor results and file-mutation receipts into the next task's prompt under hard mutation-count and character budgets?

## dependencyHandoff
**Path/Symbol:** `packages/scheduler/src/index.ts` (`dependencyHandoff`, `factoryFileMutations`) (:79–140).
**Signature:** `export function dependencyHandoff(document: FactoryDocument, task: FactoryTask, bounds: { maxMutations: number; maxChars: number }): string`.
**Data Shape:** reads `dependency.output` (summary/details/artifacts/mutations) per `task.dependencyIds` order; mutations sorted by `commitOrder`; bounds defaults `maxDependencyMutations=32`, `maxDependencyContextChars=24000`.

### Decisive source
```ts
for (const mutation of [...output.mutations].sort((left, right) => left.commitOrder - right.commitOrder)) {
    if (includedMutations >= bounds.maxMutations) { omittedMutations += 1; continue }
    includedMutations += 1
    lines.push(renderMutation(mutation))
}
...
if (omittedMutations > 0) lines.push(`[${String(omittedMutations)} additional mutation receipts omitted]`)
const complete = lines.join('\n\n')
if (complete.length <= bounds.maxChars) return complete
const marker = `[Dependency handoff truncated at ${String(bounds.maxChars)} characters]`
if (marker.length >= bounds.maxChars) return boundedText(marker, 0, bounds.maxChars).text
const body = boundedText(complete, 0, bounds.maxChars - marker.length - 1).text
return `${body}\n${marker}`
```

**Flow:** collect dependency tasks → per dependency emit heading, summary, optional details/artifacts, commit-order-sorted receipt lines up to `maxMutations` (counting the REST as omitted) → join → if over `maxChars`, truncate the BODY to reserve room for an exact-length marker appended after a newline. Root tasks (no deps) get literal `'None.'`. Receipts come from `factoryFileMutations(settled session events)` — the session's receipt-aware mutation ledger, NOT shell/external changes.
**Invariant:** The truncation marker is guaranteed to fit INSIDE the budget (body gets `maxChars - marker.length - 1`), so downstream prompts never exceed the configured context bound even in the pathological tiny-budget case; omission is always DISCLOSED with an exact count, never silent.
**Probe:** `packages/scheduler/tests/scheduler.spec.ts` "normalizes Session receipts in commit order and carries them into a bounded dependency handoff" (pins `'Change #1: create src/a.ts'` present, `'Change #2:'` absent, `'1 additional mutation receipts omitted'`, and the 80-char case asserting exact `toHaveLength(80)`). Deterministic from repo root: `grep -c 'additional mutation receipts omitted' packages/scheduler/src/index.ts` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-dsh-factory", query: "dependencyHandoff", limit: 5, fields: ["signature", "name", "file"] });
```
(CLI equivalent verified via sibling name-pattern queries on this project.)

## Verdict
Adopt disclosed-omission bounded handoff rendering + commit-order receipt normalization. Adapt the receipt schema to host diff tracking. Omit cordis message-source declaration merging.
