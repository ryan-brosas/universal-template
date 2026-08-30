<!-- capsule-v2 -->
# Grouped-sort NULLS contract — one mapping, three dialect branches, count-desc as a first-class direction

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How are group buckets ordered when the sort key is a group key itself, including by-count and per-dialect NULL placement?

## Outer-query sort block over g.<alias>
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts:list` :589-689.
**Signature:** iterates resolved `sorts`; SKIPS any sort whose column is not a group key (:591-593).
**Data Shape:** directions: `asc | desc | count-asc | count-desc` (non-asc/desc = count sorts).

### Decisive source
```ts
// :663-668 — count-desc is a REAL direction: order by the group SIZE first,
// then the key; nulls LAST for desc / FIRST otherwise (pg reference):
outerQb.orderBy('g.count', dir === 'count-desc' ? 'desc' : 'asc',
                dir === 'count-desc' ? 'LAST' : 'FIRST');
outerQb.orderBy(raw('??.??', ['g', getAs(column)]), sort.direction, 'FIRST');

// :674-679 — mssql NULL-ordering inversion, fixed with an explicit CASE bucket
// (comment :646-651: PG treats NULLs as largest — ASC→NULLS last, DESC→NULLs
// first; knex drops explicit NULLS for raw-column orderBy so MSSQL falls back
// to its own default (NULLs smallest) and group ORDER DIVERGES):
outerQb.orderByRaw(
  `CASE WHEN [g.key] IS NULL THEN 1 ELSE 0 END ${dir}, ([g.key]) ${dir}`);

// :682-685 — everyone else: explicit NULLS FIRST/LAST derived ONLY from dir:
outerQb.orderBy(raw('??.??', ['g', getAs(column)]), dir,
  dir === 'desc' ? 'LAST' : 'FIRST');
```
User/CreatedBy/LastModifiedBy keys take a parallel branch (:595-661) where the key expression itself is the REPLACE-chain display-name resolver (see groupby-user-display-sort).

**Flow:** resolve sorts (xwhere → sortArr → view Sort.list fallback :506-514) → skip non-group-key sorts → per entry choose count-sort vs value-sort branch → dialect NULLS handling.
**Invariant:** (1) Direction→NULL-placement mapping exists at ONE place and pg semantics are canonical; MSSQL compensates with a synthetic bucket. (2) Count-sorts ALWAYS emit TWO keys (count first, key second as tiebreaker). (3) Sorting by a non-grouped column is silently ignored — not an error.
**Probe:** No unit tests upstream. Deterministic probe: rendered mssql SQL contains `CASE WHEN ... IS NULL THEN 1 ELSE 0 END` for value sorts; sqlite shows `nulls FIRST/LAST`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "g.count orderBy", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.list Function group-by.ts 109-724 (:589-689)
```

## Verdict
Adopt the single-source NULLS mapping + two-key count sorts. Adapt direction enum to host API. Caveat: no direct tests at pin; graph range verified live.
