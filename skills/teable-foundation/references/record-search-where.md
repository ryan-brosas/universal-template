<!-- capsule-v2 -->
# Record search WHERE planning — how does teable turn a free-text query into a Postgres predicate that uses the right access path per field type?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How does a record search build a correct, index-usable SQL WHERE clause that dispatches on cell type and routes to a generated full-text/substring access path when one is available?

## Field-type dispatch + access-path routing
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/repository/RecordSearchWhereBuilder.ts` — `buildRecordSearchWherePlan` (503–548), `buildFieldSearchCondition` (257–334), `buildGeneratedTextSearchCondition` (457–496), `buildGeneratedTsvectorSearchCondition` (370–432), `buildDefaultSearchCondition` (434–455).
**Signature:** `buildRecordSearchWherePlan(table, recordSearch?, options?): Result<RecordSearchWherePlan, DomainError>` where `RecordSearchWherePlan = {condition: Expression<SqlBool>|null, usedAccessPath: 'default'|'generated_text'|'generated_tsvector'}`.
**Data Shape:** `recordSearch.search` carries `.value` (the query string) and `searchesAllFields()`; `options.searchAccessPath` is an `IRecordSearchAccessPath` (`{kind:'generated_text', generatedColumnName, provider, coveredFieldIds[], searchScope}` or `{kind:'generated_tsvector', generatedColumnName, languageConfig, coveredFieldIds[], searchScope}`). Fields resolve via `search.resolveFields(table, {visibleFieldIds})`.

### Decisive source
```ts
// Routing ladder: generated_text first, then generated_tsvector, then default
const generatedTextCondition = yield* buildGeneratedTextSearchCondition(resolvedFields, recordSearch, options?.searchAccessPath, tableAlias);
if (generatedTextCondition) return ok({ condition: generatedTextCondition, usedAccessPath: 'generated_text' });
const searchAccessPathCondition = yield* buildGeneratedTsvectorSearchCondition(resolvedFields, recordSearch, options?.searchAccessPath, tableAlias);
if (searchAccessPathCondition) return ok({ condition: searchAccessPathCondition, usedAccessPath: 'generated_tsvector' });
return ok({ condition: yield* buildDefaultSearchCondition(resolvedFields, recordSearch, tableAlias), usedAccessPath: 'default' });
// generated_text: pg_bigm indexes LIKE only — prefilter by the normalized document, keep the field predicate as the result oracle
const indexedPrefilter = sql`${documentRef} LIKE lower(${pattern}) ESCAPE '\\'`;
return sql`(${indexedPrefilter}) AND (${exactCondition})`;
```
**Flow:** resolve visible fields → try `generated_text` (provider min probe length: pg_trgm≥3, pg_bigm≥2; only if every resolved field is covered and scope matches) → try `generated_tsvector` (`websearch_to_tsquery(lang, value)` `@@` the generated column; scoped mode ANDs a `to_tsvector` over the field document parts) → fall back to `default` which ORs one predicate per field. Per-field dispatch: `button` and boolean-in-all-fields → skip; structured string → jsonb `#>> '{title}'` (single) or recursive jsonb array flatten (multiple); number → `ROUND(col::numeric, precision)::text ILIKE`; dateTime → range `col >= start AND col < end`; multipleSelect → whole-cell `::text ILIKE` (sargable against gin_trgm); longText → `REPLACE`-normalized ILIKE; else plain `col ILIKE`. All ILIKE patterns escape `%`/`_` wildcards.
**Invariant:** the generated access path is only used when it covers EVERY resolved field (a partial-coverage path silently falls back to default rather than returning wrong rows); the field-level predicate remains the result oracle and the generated index is only a prefilter; a probe shorter than the provider minimum never uses the index; the `usedAccessPath` flag lets callers know which path ran.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/repository/RecordSearchWhereBuilder.jieba.integration.spec.ts` (native pg_jieba tsvector semantics, gated on `TEABLE_V2_RUN_SEARCH_VECTOR_JIEBA_INTEGRATION=1`); `RecordSearchWhereBuilder.pglite.spec.ts`; `RecordSearchExplain.db.spec.ts` (EXPLAIN-based access-path assertions).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildRecordSearchWherePlan buildGeneratedTextSearchCondition", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the routing ladder (generated access path only when full-coverage, else default), the per-cell-type predicate dispatch, the index-prefilter + field-oracle AND pattern, wildcard escaping, and the `usedAccessPath` result flag. Adapt the provider minimum-probe-length constants, jsonb shapes, and date range semantics to your schema. Omit teable's jieba/tsvector language config specifics unless building CJK full-text search.
