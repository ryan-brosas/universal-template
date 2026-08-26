<!-- capsule-v2 -->
# RecordUpdateBuilder — how do you turn a mutation spec into UPDATE SQL plus the full computed-propagation impact plan?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** How does a single-record cell mutation become (a) SET clauses + side-effect SQL and (b) the link-diff/exclusivity/seed/lock metadata the repository needs BEFORE executing?

## Plan-vs-compiled split + impact collector
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/query-builder/update/RecordUpdateBuilder.ts:build` (:127–160), `:buildMutationPlan` (:162–214), `:collectUpdateImpact` (:216–268).
**Signature:** `build({table, tableName, tableDisplayName?, mutateSpec: ICellValueSpec, recordId, context}): Promise<Result<RecordUpdateSqlResult, DomainError>>`; `buildMutationPlan(...)` returns raw `setClauses` (for repositories needing their own UPDATE...RETURNING); `collectUpdateImpact(...)` returns `RecordUpdateImpact`.
**Data Shape:** `RecordUpdateImpact = { impactHint: {valueFieldIds, linkFieldIds}, extraSeedRecords, linkChanges, valueFieldIds, linkedRecordLocks, exclusivityConstraints }`. `valueFieldIds` = changed NON-link fields; `linkFieldIds` = relation-changing link fields. Context flag `assumeEmptyLinkState?: boolean`.

### Decisive source
```ts
const mutateVisitor = CellValueMutateVisitor.create(db, table, tableName, { recordId, actorId, now, ... });
yield* mutateSpec.accept(mutateVisitor);            // visitor emits per-field SQL fragments
const { setClauses, additionalStatements, changedFieldIds } = statementsResult.value;
// impact pass SEPARATE from SQL pass:
const valueFieldIds = changedFieldIds.filter(f => !isLink(f));
const { linkChanges, exclusivityConstraints } = await collectLinkChanges({...});
impactHint = buildImpactHint(valueFieldIds, linkChanges.relationChangeFieldIds);
```
Main UPDATE always `.where('__id', '=', recordId)`; additional statements get generic descriptions ("Additional statement N") in plan form.
**Flow:** accept spec → CellValueMutateVisitor builds setClauses/statements → collectUpdateImpact loads current links → diff → derive locks/exclusivity/seeds → wrap compiled main UPDATE.
**Invariant:** The impact collection is a READ of current link state — it must run in the same transaction/snapshot discipline as the eventual write or the diff is stale. `changedFieldIds` drives computed seeding; splitting value vs link fields is what lets the planner distinguish "recompute cells" from "recompute symmetric relations".
**Probe:** No dedicated builder unit spec — behavior pinned indirectly by `PostgresTableRecordRepository.update.spec.ts` (full updateManyStream flows) and exclusivity specs; caveat recorded.

## Existing-link reader (per-relationship)
**Path/Symbol:** `RecordUpdateBuilder.ts:loadExistingLinkRecordIds` (:470–576).
**Signature:** `async (db, tableName, recordId, field: LinkField): Promise<Result<string[], DomainError>>`.
**Data Shape:** read strategy by relationship — junction (`manyMany || oneMany&&oneWay`): SELECT foreignKey FROM junction WHERE selfKey=recordId ORDER BY `<orderCol> ?? '__id'`; manyOne/oneOne with `foreignKeyName === '__id'`: reads symmetric host table selecting `__id` WHERE selfKey=recordId ORDER BY `` `${selfKey}_order` `` (DERIVED column name); normal manyOne/oneOne: single-row SELECT fk FROM own table; oneMany two-way: SELECT `__id` FROM foreign table WHERE selfKey=recordId.

### Decisive source
```ts
if (relationship === 'manyOne' || relationship === 'oneOne') {
  if (foreignKeyResult.value === RECORD_ID_COLUMN) {
    const orderColumnNameForSymmetric = field.hasOrderColumn()
      ? `${selfKeyResult.value}_order` : null;      // derived, NOT field.orderColumnName()
    // SELECT __id FROM <fkHostTable> WHERE <selfKey> = recordId ORDER BY <derived>
  }
  // else: SELECT <fk> FROM <tableName> WHERE __id = recordId  → [value] or []
}
```
Non-string/empty values filtered out; infrastructure failures wrapped as `domainError.infrastructure`.
**Flow:** resolve relationship → choose host table + key columns → order-preserving read → return foreign record ids.
**Invariant:** The symmetric-read path derives `{selfKey}_order` instead of using the field's order column name — porters who reuse `orderColumnName()` there break ordered symmetric links. Order matters because diff/reorder detection compares sequences.
**Probe:** exercised via `PostgresTableRecordRepository.update.spec.ts` recording-driver assertions on emitted queries (e.g. :1677–1766 flow); no direct unit spec for this private helper — caveat stands.

## Link-change collection + lock derivation
**Path/Symbol:** `RecordUpdateBuilder.ts:collectLinkChanges` (:360–430), `LinkValueCollectorVisitor` (:270–346), `:buildLinkedRecordLocksFromLinkChanges` (:582–614), `:buildExtraSeedRecordsFromLinkChanges` (:432–459), `:collectLinkedRecordLocksForUpdate` (:620–633).
**Signature:** `collectLinkChanges({db, table, tableName, recordId, mutateSpec, assumeEmptyLinkState?}): Promise<Result<{linkChanges, exclusivityConstraints}, DomainError>>`; shared entry `collectLinkedRecordLocksForUpdate(params)` used by BOTH single and batch builders to keep lock behavior consistent.
**Data Shape:** `LinkValueCollectorVisitor` harvests ONLY link mutations: `visitSetLinkValue` records `fieldId → spec.value.toValue()`; `visitClearFieldValue` records `null` FOR LINK FIELDS ONLY; `visitSetLinkValueByTitle` deliberately records NOTHING (title must resolve to ids before this layer). All non-link visits are no-ops.

### Decisive source
```ts
for (const linkChange of collected.linkChanges) {
  if (linkChange.changeType === 'reorder') continue;   // reordering takes NO advisory locks
  const foreignTableId = linkChange.symmetricTableId?.toString();
  for (const id of linkChange.addedForeignRecordIds)   locks.push({foreignTableId, foreignRecordId: id});
  for (const id of linkChange.removedForeignRecordIds) locks.push({foreignTableId, foreignRecordId: id});
}
```
Exclusivity constraints collected per changed link field via `LinkExclusivityConstraintCollector.create({recordId, existingLinkIds, newRawValue})`; only pushed when `hasConstraint`. Extra-seed map dedupes by tableId+recordId string keys.
**Flow:** harvest link values → early-exit when none → per field: load existing ids (or `[]` under assumeEmptyLinkState) → run change + exclusivity collectors → merge into aggregate → derive locks skipping reorders → derive seeds from affectedForeignRecords.
**Invariant:** reorder-only changes must NOT acquire foreign locks (they don't create/remove relations; locking would serialize pure reorders and risk deadlocks). Under `assumeEmptyLinkState` the existing-state read is skipped ENTIRELY (restore/import fast path) — the caller guarantees emptiness; using it on live data silently corrupts the diff.
**Probe:** `PostgresTableRecordRepository.update.spec.ts` :1677 'skips existing link reads for restore-style updateManyStream batches' — recording driver asserts the existing-link SELECT disappears while the FK backfill UPDATE remains; `visitors/LinkExclusivityConstraintCollector.spec.ts` pins constraint derivation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "collectLinkChanges loadExistingLinkRecordIds buildLinkedRecordLocksFromLinkChanges", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the spec→visitor→plan pipeline with separate impact metadata (locks skip reorders; ByTitle not collected pre-resolution; assumeEmptyLinkState skips reads entirely), and the per-relationship existing-link reader including the derived `{selfKey}_order` symmetric ordering. Adapt `ICellValueSpec`/visitor plumbing to your command layer. Omit kysely specifics and teable's domain-error vocabulary where your host has equivalents. Coverage caveat: no dedicated unit spec for RecordUpdateBuilder itself; pinned via repository-level update/exclusivity suites listed above.
