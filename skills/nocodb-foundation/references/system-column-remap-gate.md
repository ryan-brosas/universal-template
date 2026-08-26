<!-- capsule-v2 -->
# NocoDB system-column remap — how do you recognize a NocoDB-created table during re-introspection without false positives?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** When re-populating metadata for a source NocoDB manages, which physical columns get remapped to system UITypes, and what admission test prevents misclassifying user tables that merely have a `created_at`?

## NocoDB system-column remap
**Path/Symbol:** `packages/nocodb/src/helpers/populateMeta.ts` — `NC_SYSTEM_COL_UIDT` map (:342–349), detection + remap loop (:380–393).
**Signature:** `isNcCreatedTable = Object.keys(NC_SYSTEM_COL_UIDT).every(name => columnNameSet.has(name))`.
**Data Shape:** six required columns: `created_at→CreatedTime`, `updated_at→LastModifiedTime`, `created_by→CreatedBy`, `updated_by→LastModifiedBy`, `nc_order→Order`, `META_COL_NAME (__nc_meta)→Meta`; comment at :340 states "Detect NocoDB-created tables by presence of all 6 system columns."

### Decisive source
```ts
// :381–393 — ALL-six gate then per-column remap:
const isNcCreatedTable = Object.keys(NC_SYSTEM_COL_UIDT).every((name) =>
  columnNameSet.has(name),
);
for (const column of columns) {
  // Remap NocoDB system columns to their proper UITypes
  if (isNcCreatedTable && NC_SYSTEM_COL_UIDT[column.cn]) {
    column.uidt = NC_SYSTEM_COL_UIDT[column.cn];
    column.system = true;
  } else if (!column.uidt) {
    column.uidt = getColumnUiType(source, column);
  }
}
```

**Flow:** introspected columns arrive with raw SQL types → build a Set of physical names → only when EVERY one of the six marker names exists does the table qualify as NocoDB-created → qualifying tables get those columns' uidt OVERWRITTEN to the semantic UITypes and flagged `system: true`; every other column falls back to type inference (`getColumnUiType`) when uidt is missing.
**Invariant:** The gate is conjunction-of-all-six, not any-single-match. A plain user table with `created_at`/`updated_at` must NOT have them converted to hidden CreatedTime system fields — partial matches leave columns untouched. Remap also mutates the shared `columns` array in place BEFORE `mapDefaultDisplayValue(columns)` and Column.insert, so ordering of these steps is load-bearing.
**Probe:** `grep -c "isNcCreatedTable && NC_SYSTEM_COL_UIDT" packages/nocodb/src/helpers/populateMeta.ts` → `1`.
**Coverage caveat:** grep-derived; no direct unit spec pins this ladder.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "NC_SYSTEM_COL_UIDT getColumnUiType", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the all-six conjunction admission and in-place remap-before-display-value-selection ordering; adapt the exact marker names (META_COL_NAME constant) to host schema; omit the pg bytea colMeta special-case (:329–334) which is dialect bookkeeping.
