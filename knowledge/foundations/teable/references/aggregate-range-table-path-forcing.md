<!-- capsule-v2 -->
# aggregate-range-table-path-forcing — Why must a paginated aggregate never use the tableCache query-model path?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does aggregation over `[offset, offset+limit)` guarantee the BASE CTE holds exactly the target rows?

## Paginated range forces the table path
**Path/Symbol:** `apps/nestjs-backend/src/features/record/query-builder/record-query-builder.service.ts:createRecordAggregateBuilder` (:228-306, force at :249-253).
**Signature:** `async createRecordAggregateBuilder(from, options: ICreateRecordAggregateBuilderOptions): Promise<{qb, alias, selectionMap}>` — `usePaginatedRange = limit !== undefined`.
**Data Shape:** when a row range is requested, `effectiveUseQueryModel` is forced `false`; `paginationMode: 'full'` is passed so offset+limit land INSIDE the BASE CTE.

### Decisive source
```ts
const usePaginatedRange = limit !== undefined;
// The tableCache path skips applyBasePaginationIfNeeded, which would silently
// aggregate the entire view instead of the requested [offset, offset+limit)
// slice. Force the table path whenever a row range is requested.
const effectiveUseQueryModel = usePaginatedRange ? false : useQueryModel;
...
paginationMode: usePaginatedRange ? 'full' : undefined,
```

**Flow:** detect `limit` → override useQueryModel → build with `'full'` pagination (offset applied inside BASE) → aggregate select → filter → aggregationQuery.appendBuilder (groupBy deliberately NOT passed; grouping handled by GroupQuery afterwards) → per-group orderAggregateByGroup.
**Invariant:** the in-source comment IS the contract: the tableCache context skips base pagination entirely, so any paginated-range request routed there aggregates the WHOLE view. The comment also documents that this silent-wrong-result bug was real and was closed by forcing the path, not by adding pagination to tableCache.
**Probe:** upstream spec `record-query-builder-group-quoting.spec.ts:buildGroupedAggregateSql` drives `createRecordAggregateBuilder('permission_view', {...})` through a preconfigured builder; static check `grep -n 'effectiveUseQueryModel' ...service.ts` → :250/:253 only.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"teable","query":"createRecordAggregateBuilder","limit":5,"detail":"ids"}'
```

## Verdict
Adopt "range aggregates must run on the fully-paginated path" as a routing rule. Adapt flag names to your builder options. Omit teable's view-materialization (`tableCache`) specifics.
