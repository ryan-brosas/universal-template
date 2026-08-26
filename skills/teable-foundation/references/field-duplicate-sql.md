<!-- capsule-v2 -->
# Field-duplication SQL strategy — how do you copy a field's values (and its link relationships) entirely in SQL when a field is duplicated?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** Which field types get value copies, which are skipped, and how does link duplication differ between junction and FK storage?

## FieldValueDuplicateVisitor + LinkFieldValueDuplicateVisitor
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/FieldValueDuplicateVisitor.ts` — class (:58), `generateSimpleCopy` (:86–92), visitLinkField (:193–218); `visitors/LinkFieldValueDuplicateVisitor.ts` — routing (:44–57), junction copy (:63–96), FK copy (:103–115).
**Signature:** `FieldValueDuplicateVisitor.create(db, {schema, tableName, sourceDbFieldName, targetDbFieldName, newField?}).visit(field) → Result<CompiledQuery[]>`; exported from package index for reuse.
**Data Shape:** three-way classification: STORABLE (text/number/rating/checkbox/date/selects/user/attachment/button? no—button skips) ⇒ `UPDATE t SET "new" = "old"`; COMPUTED + SYSTEM/AUTO (formula, rollup, conditional*, autoNumber, createdTime/By, lastModifiedTime/By) ⇒ `[]` (values recompute themselves); LINK ⇒ value copy + relationship copy.

### Decisive source
```ts
// link duplication routes on RELATIONSHIP STORAGE, not display columns:
const usesJunctionTable =
  relationship === 'manyMany' || (relationship === 'oneMany' && sourceField.isOneWay());
if (usesJunctionTable) {
  // INSERT INTO new_junction (selfKey, foreignKey [, order])
  // SELECT same FROM old_junction            ← whole-table copy, order col included
} else {
  // UPDATE table SET "__fk_new" = "__fk_old"  ← manyOne / oneOne / two-way oneMany
}
```

**Flow:** duplicate-field flow calls the visitor with the NEW link field present ⇒ statements = [value-column copy, relationship copy]; without a new link target it degrades to the simple value copy; junction names resolve via `fkHostTableNameString()` with schema splitting and explicit error on malformed `'schema.table'`.
**Invariant:** computed fields NEVER get row copies (their storage is derived); the relationship copy is UNFILTERED (every relation row clones, including ones whose records were since deleted — acceptable because duplication targets consistency of the snapshot moment).
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/visitors/FieldValueDuplicateVisitor.spec.ts:32 'generates simple copy SQL...skips computed/system fields'`, :84 fallback without link target, :113 combined copy+relationship; `LinkFieldValueDuplicateVisitor.spec.ts:28 junction w/ order columns`, :62 one-way one-many + malformed host name error, :98 fk-column copy.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "FieldValueDuplicateVisitor generateSimpleCopy generateJunctionTableCopy generateFkColumnCopy", limit: 10 });
```

## Verdict
Adopt the three-way storable/computed/link classification and storage-routed link duplication with order-column inclusion; adapt field-type enumeration to host; omit the malformed-name error shape if your identifiers are pre-validated upstream.
