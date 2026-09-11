<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/generic.ts` :169–195 (`generateNestedRowSelectQuery`, `singleQueryList`, `singleQueryRead`, `extractColumns`, `extractColumn`) + `db/BaseModelSqlv2.ts` :207 (`bulkAggregate?: boolean`) + :7295–7306 + :7389–7400.

# Question
Which client methods are deliberate throw-stubs, and how does the bulkAggregate exec flag change row post-processing?

## Path / Symbol
`GenericDBQueryClient.{generateNestedRowSelectQuery, singleQueryList, singleQueryRead, extractColumns, extractColumn}`; `execAndParse(qb, null, {bulkAggregate: true, ...})`.

## Signature
```ts
generateNestedRowSelectQuery(_param: any): Knex.Raw<any> { throw new Error('Not implemented'); }
async singleQueryList(...):  { throw new Error('Not implemented'); }
async singleQueryRead(...) { throw new Error('Not implemented'); }
async extractColumns(_param: any): Promise<void> { throw new Error('Not implemented'); }
```

## Data Shape
Five methods throw 'Not implemented' in the CE base — they are EE single-query-client surface (the group-by.ts:734 comment names the "EE single-query client" as ensurePaginationOrderBy's other owner). The interface declares them; the CE base makes the boundary LOUD instead of silently returning wrong shapes.

## Decisive source
generic.ts:169–195 — five consecutive throw stubs. Note extractColumns returns Promise<void> while extractColumn returns `{isArray?}` — the pair is asymmetric BY DESIGN (plural scans all columns for materialization, singular resolves one column's array-ness).
BaseModelSqlv2.ts:7295–7306 — when `options.raw || options.bulkAggregate`, execAndParse FORCE-SETS five skip flags (skipDateConversion/Attachment/SubstitutingColumnIds/User/Json = true) — aggregate rows have no per-record identity so record-shaped converters must not run.
BaseModelSqlv2.ts:7389–7400 — then the bulkAggregate branch walks every result cell and JSON.parses values that are strings starting with '{' (try/catch keeps non-JSON as-is) — THIS is the consumer side of the three dialects' JSON_OBJECT/JSON_BUILD_OBJECT/json_object row selectors: the selector emits a JSON STRING, execAndParse turns it into an object keyed by col.id/alias.

## Flow / Invariant
The wire contract a porter must keep intact: handler wrap() aliases each aggregate as col.id → selector packs {'<col.id>': value} into a JSON string column → outer query returns one row → execAndParse(bulkAggregate) string-parses it → orchestrator remaps id→title. Break any link (e.g. emitting real jsonb instead of text on mysql without UNQUOTE) and keys arrive double-encoded or un-parsed.

## Probe (direct test)
From repo root:
```
sed -n '169,195p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c 'Not implemented'   # => 5 (all five stubs in range)
grep -c 'Not implemented' packages/nocodb/src/dbQueryClient/generic.ts                        # => 6 (adds the replaceDelimitedWithKeyValue stub at :203)
grep -c 'bulkAggregate?: boolean' packages/nocodb/src/db/BaseModelSqlv2.ts                    # => 1 (:207)
sed -n '7302,7308p' packages/nocodb/src/db/BaseModelSqlv2.ts | grep -c '= true'               # => 5 (the five skip flags)
grep -n "startsWith('{')" packages/nocodb/src/db/BaseModelSqlv2.ts                            # => 1 (:7395)
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"singleQueryList singleQueryRead Not implemented","limit":3,"detail":"compact"}'
```
→ resolves generic.ts stub block.

## Verdict
**Adopt.** Port the loud-stub doctrine for cross-build surface and the string-JSON round-trip contract byte-for-byte.
