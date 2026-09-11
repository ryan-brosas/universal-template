<!-- capsule-v2 -->
# view-context-raw-selection — How does the same builder serve materialized-view reads (tableCache/view contexts) without CTE generation?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which context flags switch lookups/links/rollups from CTE columns to plain view columns?

## context 'view'|'tableCache' ⇒ shouldSelectRaw(): every computed family reads its physical/view column
**Path/Symbol:** state context stamped in manager ctor (`record-query-builder.manager.ts:19`); gates `field-select-visitor.ts:isViewContext/isTableCacheContext/shouldSelectRaw` (:76-90); consumers: lookup :243-250, link :430-437, rollup :479-486, conditional-rollup :549-556, formula :291-297; service fallback `record-query-builder.service.ts:createQueryBuilder` (:113-141).
**Signature:** `private shouldSelectRaw() { return this.isViewContext() || this.isTableCacheContext(); }`.
**Data Shape:** tableCache path = `createQueryBuilderFromTableCache` (single-table domain, NO Tables graph, NO buildFieldCtes call — the `state.getContext() === 'table'` guard at :144 skips both pagination and CTEs).

### Decisive source
```ts
if (useQueryModel) {
  try {
    builder = await this.createQueryBuilderFromTableCache(tableId, from, baseBuilder);
  } catch (error) {
    this.logger.error(`Failed to create query builder from view: ${error}, use table instead`);
    builder = await this.createQueryBuilderFromTable(...);   // degrade, don't fail
  }
}
```

**Flow:** caller requests query-model → cache/tableDomain lookup may throw → log-and-degrade to full table path → otherwise all visitors see a raw context and select stored columns directly (the view already carries precomputed values), so no link CTEs are generated at all.
**Invariant:** dual-mode is invisible to consumers: identical selectionMap keys either way; only expression VALUES differ (column refs vs CTE refs). The try/catch degradation means a missing view materialization must never 500 a read.
**Probe:** static byte-exact: `grep -n "Failed to create query builder from view" apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts` → :120; upstream spec drives the non-cache path (`group-quoting` uses `useQueryModel:false`).

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"createQueryBuilderFromTableCache","limit":3,"detail":"ids"}'
```

## Verdict
Adopt context-stamped dual-mode with silent degradation. Adapt context enum. Omit nothing.
