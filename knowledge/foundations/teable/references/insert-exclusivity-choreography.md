<!-- capsule-v2 -->
# Insert exclusivity + advisory-lock choreography — in what ORDER does the repository validate one-to-one claims and take foreign-row locks around the builder's SQL?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** Where do exclusivity validation, generated-column stripping, advisory locks, and side-effect statements sit relative to the main INSERT inside `insert()`?

## Repository-side choreography consuming RecordInsertBuilder
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/PostgresTableRecordRepository.ts:insert` (:1162–1306).
**Signature:** consumes `RecordInsertDataResult`; executes with kysely inside the unit of work.
**Data Shape:** order-critical steps: (1) buildInsertData → (2) view-order columns/values merge (`restoreValues.orders` or append-at-end defaults; explicit `options.order` overrides via recordOrderCalculator) → (3) `validateInsertExclusivityConstraints(context, db, exclusivityConstraints)` BEFORE insert → (4) `stripPhysicallyGeneratedColumnsFromInsertValues` belt-and-braces vs meta-based skip → (5) INSERT (+RETURNING when changedFieldColumns requested) → (6) restore-only autoNumber sequence sync → (7) `acquireLinkedRecordLocks(db, baseId, linkedRecordLocks)` → (8) `RecordInsertBuilder.executeStatements(db, additionalStatements)` → (9) computed update run.

### Decisive source
```ts
// Validate link exclusivity constraints for oneOne/oneMany relationships
yield* await validateInsertExclusivityConstraints(context, db, exclusivityConstraints);
...
await stripPhysicallyGeneratedColumnsFromInsertValues(db, tableName,
  collectUserAuditFieldColumnNames(table), [valuesWithViewOrder]);  // legacy GENERATED ALWAYS (T6146)
const insertedRow = changedFieldColumns.length > 0
  ? await db.insertInto(tableName).values(valuesWithViewOrder)
      .returning(buildChangedFieldReturningSelects(changedFieldColumns)).executeTakeFirst()
  : await db.insertInto(tableName).values(valuesWithViewOrder).execute(), undefined);
if (restoreValues?.autoNumber !== undefined) await syncAutoNumberSequence(db, tableName);
await acquireLinkedRecordLocks(db, baseId, linkedRecordLocks);       // AFTER own row exists
await RecordInsertBuilder.executeStatements(db, additionalStatements); // junction/FK writes AFTER locks
```
Exclusivity constraint payload from the builder (`InsertExclusivityConstraint`, :62–81): `{fieldId, foreignTableId, fkHostTableName, selfKeyName, foreignKeyName, linkedForeignRecordIds, sourceRecordId, isOneWay, usesJunctionTable}` — validation distinguishes junction-hosted vs main-table-hosted checks.
**Flow:** metadata collection (pure) → pre-insert validation → physical-column guard → main INSERT → sequence repair (restore only) → lock foreign rows → execute side-effect statements → computed propagation.
**Invariant:** Exclusivity MUST be validated before the INSERT (fail fast without a dead row); locks must be acquired AFTER inserting own row but BEFORE junction/FK statements — otherwise concurrent writers can hold foreign locks while waiting on ours. Generated-column strip is deliberately duplicated: meta-level skip in builder, physical catalog probe in repository — both layers exist because legacy tables lie about meta.
**Probe:** `PostgresTableRecordRepository.insert.pglite.spec.ts` (:372/:430/:479/:525 — real-Postgres insert flows incl. returning paths); `PostgresTableRecordRepository.exclusivity.spec.ts` :79–170 (oneOne/oneMany duplicate detection matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "validateInsertExclusivityConstraints acquireLinkedRecordLocks stripPhysicallyGeneratedColumnsFromInsertValues", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the step ordering as a contract: validate-exclusive → strip-generated → insert → sequence-sync-if-restore → lock-linked → side-effects → propagate-computed, plus the double-layer generated-column defense. Adapt lock primitives to your DB (upstream uses pg_advisory locks keyed by baseId+table+record). Omit teable's view-order bootstrap specifics already covered by `view-order-bootstrap`. Coverage caveat: pglite integration specs pin runtime behavior; no runner was available in this environment to re-execute them (deterministic evidence only).
