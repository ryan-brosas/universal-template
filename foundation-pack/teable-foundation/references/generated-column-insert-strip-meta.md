<!-- capsule-v2 -->
# Generated-column insert strip (T6146) — how do you write system-computed fields without ever colliding with PostgreSQL GENERATED ALWAYS columns?

**Source:** teable AGPL-3.0 `develop@06a4461e2bc5`; Codebase Memory `teable`. **Question:** Which fields must be omitted from an explicit INSERT, decided by which mechanism, and why is the decision made twice?

## Field-type-scoped generated probe
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/isPersistedAsGeneratedColumn.ts:isPersistedAsGeneratedColumn` (:92–94) + `PersistedAsGeneratedColumnVisitor` (:17–88).
**Signature:** `(field: Field): Result<boolean, DomainError>` via `field.accept(visitor)`.
**Data Shape:** ONLY these field types can answer true: Formula, CreatedTime, LastModifiedTime, CreatedBy, LastModifiedBy, AutoNumber — each delegates to `field.isPersistedAsGeneratedColumn()`; every other type hard-codes `false` (incl. Lookup/ConditionalLookup with an explicit comment that persisted computed ≠ generated).

### Decisive source
```ts
visitFormulaField(field: FormulaField): Result<boolean, DomainError> {
  return field.isPersistedAsGeneratedColumn();      // meta-driven
}
// ...same for createdTime / lastModifiedTime / createdBy / lastModifiedBy / autoNumber
override visitLookupField(_field: LookupField) { return ok(false); }
```
Consumers: RecordInsertBuilder skips BOTH the user-snapshot write (:252–256) and time-field write (:285–288) when true; BatchRecordUpdateBuilder excludes generated lastModifiedBy fields from its snapshot pre-scan (:202–210).
**Flow:** builder reaches a system-computed field → probe visitor → true ⇒ `continue` (column absent from INSERT; DB generates it) → false ⇒ explicit value written.
**Invariant:** PostgreSQL rejects ANY explicit value for `GENERATED ALWAYS` columns — writing your computed snapshot there aborts the whole INSERT. The probe is deliberately META-level (field metadata), not catalog introspection, so it stays O(1) per row in hot loops.
**Probe:** `insert/RecordInsertBuilder.userFields.spec.ts` :223–280 'should omit CreatedBy/LastModifiedBy columns when persisted as generated (T6146)' — asserts values lack both columns AND `userFieldColumns` is empty while system columns remain.

## Physical belt-and-braces at the repository layer
**Path/Symbol:** `PostgresTableRecordRepository.ts:stripPhysicallyGeneratedColumnsFromInsertValues` call site :1263–1270 (single insert) and bulk twin.
**Data Shape:** after the builder ran, the repository STILL strips audit columns (`collectUserAuditFieldColumnNames(table)`) whose physical column is generated, probing the catalog.

### Decisive source
```ts
// Legacy CreatedBy/LastModifiedBy columns may still be GENERATED ALWAYS even when
// field meta says otherwise — strip them so PostgreSQL accepts the INSERT (T6146).
await stripPhysicallyGeneratedColumnsFromInsertValues(
  db, tableName, collectUserAuditFieldColumnNames(table), [valuesWithViewOrder]);
```
**Flow:** meta-based skip inside builders (cheap, per-row) → physical catalog strip once per statement batch (authoritative).
**Invariant:** Two layers exist because legacy tables migrated before the meta flag can disagree with the real schema. A porter who keeps only one layer works on fresh tables and silently fails on migrated ones. The comment text itself carries the rationale — preserve it.
**Probe:** same userFields spec pins the meta layer; the physical layer is exercised by insert pglite suites against legacy-shaped fixtures (no dedicated unit spec — caveat recorded).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "isPersistedAsGeneratedColumn stripPhysicallyGeneratedColumnsFromInsertValues GeneratedColumnMeta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the typed-visitor meta probe scoped to exactly six field types plus the second physical-strip pass over audit columns before executing inserts. Adapt visitor plumbing to your field model; keep the six-type allowlist semantics (new field types default to false = writable). Omit teable's GeneratedColumnMeta rehydration details. Coverage caveat: direct unit spec covers the meta path; physical path pinned by integration suites only.
