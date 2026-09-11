<!-- capsule-v2 -->
# original-source-latch — Why must the pre-BASE table source survive the BASE CTE rewrite?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** After the main source is repointed at the BASE CTE, where do nested link CTEs read the physical table from?

## First write wins: originalMainSource is a latch, not a shadow
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.manager.ts:setMainTableSource` (:88-94) + `getOriginalMainTableSource` (:43-45); consumed in `field-cte-visitor.ts:fromTableWithRestriction` (:893-902).
**Signature:** `setMainTableSource(source: string): void { this.mainSource = source; if (!this.originalMainSource) { this.originalMainSource = source; } }`.
**Data Shape:** two fields; getter falls back `original ?? current`. The service sets source twice for paginated queries (physical table → `BASE_<alias>`), so ordering decides which value latches.

### Decisive source
```ts
// manager
if (!this.originalMainSource) {
  this.originalMainSource = source;
}
...
// field-cte-visitor.fromTableWithRestriction — every CTE body re-reads the ORIGINAL source:
const source =
  table.id === this.table.id
    ? this.state.getOriginalMainTableSource() ?? table.dbTableName
    : table.dbTableName;
builder.from(`${source} as ${alias}`);
if (table.id === this.table.id) {
  this.applyMainTableRestriction(builder, alias);
}
```

**Flow:** builder created from physical `dbTableName` (latch captures it) → pagination wraps source into BASE and overwrites mainSource → all later link/conditional CTE bodies call `fromTableWithRestriction`, which reads the LATCHED physical name and adds `WHERE __id IN (SELECT __id FROM BASE)` restriction.
**Invariant:** if the latch captured the CTE name instead (naive "always record first set"), nested CTEs would self-reference BASE inside its own WITH list → invalid SQL. The first-write-wins order + the id-restriction subquery are what make nested CTEs see only paged rows without reading the CTE.
**Probe:** static byte-exact: `grep -n 'originalMainSource ?? this.mainSource' record-query-builder.manager.ts` → :44; `grep -n 'getOriginalMainTableSource() ?? table.dbTableName' ../record/query-builder/field-cte-visitor.ts` → :895 region.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"fromTableWithRestriction","limit":5,"detail":"ids"}'
```

## Verdict
Adopt "latch the physical source before any wrapper rewrite; feed wrappers through a getter that prefers the original". Adapt naming. Omit teable's self-table vs foreign-table branch shape only if your builder has no cross-table scopes.
