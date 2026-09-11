<!-- capsule-v2 -->
# Unique-index duplicate remediation — how does a one-to-one link rule detect, quantify, and (with consent) clear duplicate links before creating its unique index?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** What makes unique-index repair safe when live data violates uniqueness?

## UniqueIndexRule
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/UniqueIndexRule.ts` — isValid with pre-count (:124–155), manualRepair (:223–273), `countDuplicateValues` (:275–322), `clearDuplicateValues` (:362–382), up() drop-then-create (:210–216).
**Signature:** `UniqueIndexRule.forFkColumn(field, columnName, parent, relationshipType?, targetTable?)`; index name convention `index_${columnName}`; repair resolution enum `'clear_duplicate_values'`.
**Data Shape:** duplicate summary `{duplicateGroups, duplicateRows}` where rows = SUM(group_count−1); both surfaced in i18n values and drive the hint copy.

### Decisive source
```sql
-- clearDuplicateValues: keep FIRST row per value (lowest __id), NULL the rest
WITH duplicate_rows AS (
  SELECT "__id", ROW_NUMBER() OVER (PARTITION BY col ORDER BY "__id") AS rn
  FROM tbl WHERE col IS NOT NULL
)
UPDATE tbl AS t SET col = NULL FROM duplicate_rows d
WHERE t."__id" = d."__id" AND d.rn > 1;
```

**Flow:** validation: index missing OR not-unique ⇒ count duplicates FIRST so the failure can distinguish 'clean missing index' from 'data-blocked'; duplicates present ⇒ coded failure `unique_index_duplicate_values` + MANUAL hint (user must confirm clearing) → on confirm: clear via window-function update → re-run up() which DROPs any non-unique incumbent index then CREATE UNIQUE INDEX IF NOT EXISTS.
**Invariant:** auto-repair NEVER creates a unique index over violating data and NEVER deletes rows — it nulls the LINK side only ('keeps first link, clears later duplicates'); drop-before-create handles the exists-but-not-unique upgrade path.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/schema/rules/field/SchemaRules.pglite.spec.ts:1440 'should require manual repair when duplicate values exist behind a non-unique index'`, :1489 'should manually clear duplicate values and create a unique index', :1418 non-unique→unique replacement.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "UniqueIndexRule countDuplicateValues clearDuplicateValues createDuplicateValuesValidation", limit: 10 });
```

## Verdict
Adopt quantified duplicate detection feeding a confirm-gated null-out strategy plus drop-and-recreate index upgrades; adapt retention ordering key (__id) to host row identity; omit i18n envelopes.
