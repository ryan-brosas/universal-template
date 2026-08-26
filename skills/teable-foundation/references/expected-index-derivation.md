<!-- capsule-v2 -->
# Expected-index derivation — how does teable turn a query shape into the set of indexes it SHOULD have, then diff it against pg_indexes?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Before recommending an index, you must know which indexes the workload already warrants. How do you derive expected btree/gin_trgm/composite candidates from a structured query shape and detect missing/invalid ones?

## Shape→candidate derivation + catalog diff
**Path/Symbol:** `packages/v2/adapter-table-query-ops-postgres/src/indexInspection.ts` — `PostgresTableQueryIndexInspector.inspect` (17–78), `collectExpectedIndexCandidates` (127–154), `collectBtreeAccessPathFields` (212–276), `addWhereIndexCandidates` (278–360), `addOrderIndexCandidates` (395–410), `addSearchIndexCandidates` (412–437), `selectCompositeBtreeFields` (439–449), `hasMatchingIndex` (471–492), `parseIndexColumns` (494–502), `matchesIndexColumn` (504–512), `containsColumnReference` (514–524).
**Signature:** `inspect(ctx, table, shape): Promise<Result<TableQueryIndexInspection, DomainError>>`; inspection = `{state:'ready'|'missing'|'invalid', usefulIndexes[], missingIndexCandidates[], abnormalIndexes[]}`.
**Data Shape:** candidate = `{fieldId?, fieldDbName?, fields[{fieldDbName, direction?, role?, sourceKind?, formulaFieldId?, formulaFunctionNames?, formulaPredicatePushdown?}], kind:'btree'|'gin_trgm', accessPath:'single_field'|'composite'|'expression', reason}`. Shape snapshot carries `whereShape.fields[{fieldId, operatorFamily, sourceKind, formula?}]`, `orderShape.fields[{fieldId, direction, source}]`, `searchShape{allFields}`.

### Decisive source
```ts
// composite: equality filters first, then order (or first range), deduped, capped at 3
const fields = [...equalityFilterFields, ...(orderFields.length ? orderFields : rangeFilterFields.slice(0,1))];
return dedupeFields(fields).slice(0, 3);
// text_contains → gin_trgm; text_prefix → btree; equality/range/selection/empty/link/formula_result → btree
if (field.operatorFamily === 'text_contains') addExpectedIndexCandidate(candidates, [resolve(...)], 'gin_trgm', ...);
else if (field.operatorFamily === 'text_prefix') addExpectedIndexCandidate(candidates, [resolve(...)], 'btree', ...);
// a single-field candidate is suppressed if the composite already covers it:
if (!isCoveredByCompositeCandidate(resolved, compositeFields)) addExpectedIndexCandidate(...);
// matching: gin_trgm needs column ref + 'using gin' + 'gin_trgm_ops'; btree parses USING (...) columns
if (candidate.kind === 'gin_trgm') return containsColumnReference(def, fieldDbName) && def.includes(' using gin ') && def.includes('gin_trgm_ops');
const indexColumns = parseIndexColumns(def);
return candidate.fields.every((f, i) => matchesIndexColumn(indexColumns[i], f.fieldDbName));
```

**Flow:** `inspect` reads all `pg_indexes` rows for the physical table → `collectExpectedIndexCandidates` derives the expected set (composite btree from equality+order/range, per-field btree for where/order, gin_trgm for text_contains and search fields, expression btree for stable+sqlTranslatable+expressionIndexable formula fields) → diff: missing = expected minus matching existing; also query `pg_index` for `NOT indisvalid` rows → `abnormalIndexes` → state = `invalid` if any abnormal, else `missing` if any missing, else `ready`.
**Invariant:** expected candidates are keyed by `kind:accessPath:fieldDbName:direction:role:sourceKind` (dedup via Map); a composite candidate suppresses redundant single-field ones (`isCoveredByCompositeCandidate`); gin_trgm detection requires the exact `gin_trgm_ops` operator class, not merely a GIN index; btree matching parses the `USING (...) ` column list and compares positionally with quoted-or-bare tolerance.
**Probe:** `repositories.spec.ts` and the indexInspection path are exercised through the advisor integration specs; `indexInspection.ts` has no dedicated unit spec — the derivation is pinned by `advisor.integration.spec.ts` (811L) and `searchVector.integration.spec.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "collectExpectedIndexCandidates addWhereIndexCandidates selectCompositeBtreeFields hasMatchingIndex", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt shape→candidate derivation with composite suppression and strict operator-class matching; adapt operator-family vocab and the composite cap to host; omit teable's formula-expression pushdown details if the host lacks formula fields. Coverage caveat: `indexInspection.ts` is parse_partial at :25 and :39 (template-literal lines in the two SQL queries); the derivation logic is fully indexed.
