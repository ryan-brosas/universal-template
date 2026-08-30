<!-- capsule-v2 -->
# Before-image chaining — how do computed stages preserve the ORIGINAL user-mutation old values across multi-stage recomputes?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** When a computed update runs in stages (sync then outbox), how are filter-field before-images merged so later stages don't lose them?

## Extract-from-step-changes + earliest-wins merge
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedBeforeImageFromChanges.ts` — whole file (123L); consumed by `runComputedUpdate*` chains in the repository; direct test `__tests__/ComputedBeforeImageFromChanges.spec.ts`.
**Signature:** `buildBeforeImageRecordsFromStepChanges({ seedTableId, seedRecordIds, seedFieldIds, changesByStep, tableById })`; `mergeBeforeImageRecords(existing, incoming): ComputedBeforeImageRecord[]`.
**Data Shape:** `ComputedBeforeImageRecord = { recordId: RecordId, fieldValuesByDbName: Record<dbFieldName, oldValue> }`.

### Decisive source
```ts
// merge keeps the EARLIEST value per db field name:
// "existing wins over incoming for the same key" — because existing entries
// were captured closer to the original user mutation.
const merge = (records) => {
  for (const record of records) {
    ...
    for (const [dbFieldName, oldValue] of Object.entries(record.fieldValuesByDbName)) {
      if (!(dbFieldName in current.fields)) {       // first writer keeps the slot
        current.fields[dbFieldName] = oldValue;
      }
    }
  }
};
merge(existing);   // existing seeded FIRST
merge(incoming);
```

**Flow:** step changes (from ComputedFieldUpdater's StepChangeData) are filtered to seed table/records → field ids map to db field names (missing fields skipped silently) → per-record old-value objects assembled → chained stages call merge so filter-field old values captured on the user mutation survive stages that only saw computed-field events.

**Invariant:** merge order IS semantics — `existing` must be passed first; reversing arguments silently promotes later-stage stale values to "original". Empty seeds/changes short-circuit to `[]` without table lookups.

**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedBeforeImageFromChanges.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildBeforeImageRecordsFromStepChanges mergeBeforeImageRecords", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt earliest-wins merging for staged recompute history. Adapt record/field identity types. Nothing else to omit.
