<!-- capsule-v2 -->
# Conditional-rollup ALL_RECORDS fail-safe ladder — when must a conditional filter give up narrowing and refresh everything?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which conditions force a conditional rollup/lookup to abandon precise record targeting and fall back to whole-table refresh?

## getConditionalRollupImpactedRecordIds
**Path/Symbol:** `apps/nestjs-backend/src/features/record/computed/services/computed-dependency-collector.service.ts:ComputedDependencyCollectorService.getConditionalRollupImpactedRecordIds` (:747–1062).
**Signature:** `getConditionalRollupImpactedRecordIds(edge, foreignRecordIds, changeContextMap?, ctx?): Promise<string[] | typeof ALL_RECORDS>`.

### Decisive source
```ts
const MAX_CONDITIONAL_ROLLUP_SAMPLE = 10_000;                       // :72
if (uniqueForeignIds.length > MAX_CONDITIONAL_ROLLUP_SAMPLE) return ALL_RECORDS;   // :757–759
if (!filter) return ALL_RECORDS;                                    // :765–767
if (!hostFieldRefs.length) return ALL_RECORDS;                      // :770
if (hostFieldRefs.some((ref) => ref.tableId && ref.tableId !== edge.tableId)) return ALL_RECORDS; // :778
if (hostFieldMap.size !== uniqueHostFieldIds.length) return ALL_RECORDS;           // :784
// :797–805 in-source rationale comment
// Note: when any foreign-side filter column is JSON, we bail out to ALL_RECORDS.
// The values-based subquery we build below uses parameter binding which serialises JSON
// as plain text. Postgres then attempts to cast that "text" into json/jsonb ... Without
// explicit casts ... the parser errors out: invalid input syntax for type json ...
```

**Flow:** eight bail-outs precede any SQL: >10k ids, missing filter, no host field-refs, cross-table ref, unknown host/foreign fields (:788–794), JSON-typed filter columns (duplicated check :806–816 — the in-source comment explains parameter binding cannot inline typed json literals), and later unresolvable dbFieldName mapping / undefined VALUES cells (:899–901, :983). Precise path = EXISTS subquery over a `(VALUES ...) AS t(__id)` join filtered with `dbProvider.filterQuery` (:850–870); when change contexts are supplied, rows are OVERWRITTEN with new values and re-probed through a **typed CAST-per-column UNION ALL derived table** (`CAST(? AS integer/double precision/boolean/timestamp/jsonb...)`, :975–1031) so the post-write filter still matches — matched ids are UNIONed into the result (:1054–1059).
**Invariant:** Fail-safe direction is always WIDENING (over-refresh), never skipping. The typed-VALUES trick exists because binding JSON as text breaks `@>`/`?` operators on PG — a porter who binds raw objects will hit `invalid input syntax for type json`. `buildValuesTable` throws on empty values (:172–175).
**Probe:** needles verified at this pin (`MAX_CONDITIONAL_ROLLUP_SAMPLE = 10_000` :72, JSON-bailout comment :797); behavior pinned by `packages/v2/e2e/src/computed-anonymized-dead-letter-p0.e2e.spec.ts`; graph retrieval resolves :747–1062.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "getConditionalRollupImpactedRecordIds", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ladder order (cheap checks first) and the widening-only failure policy; adapt the per-dialect CAST table to your type map; omit the duplicated JSON check (dead second arm) after porting.
