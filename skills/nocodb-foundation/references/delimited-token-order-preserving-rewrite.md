<!-- capsule-v2 -->
# Source
NocoDB `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73` — `packages/nocodb/src/dbQueryClient/pg.ts` :40–86 + `sqlite.ts` :37–84 (`replaceDelimitedWithKeyValue`) + consumer `db/BaseModelSqlv2/group-by.ts` :638–657.

# Question
How can a User/CreatedBy column (comma-separated id list) be filtered or grouped by DISPLAY NAME inside SQL?

## Path / Symbol
`PGDBQueryClient.replaceDelimitedWithKeyValue({ knex, stack, needleColumn, delimiter? })`, `SqliteDBQueryClient.replaceDelimitedWithKeyValue`.

## Signature
```ts
replaceDelimitedWithKeyValue(params: { knex: CustomKnex; stack: { key: string; value: string }[];
  needleColumn: string | Knex.QueryBuilder | Knex.RawBuilder; delimiter?: string }): string
```
Returns a composed SQL STRING (.toQuery()) — not a builder.

## Data Shape
stack = base-user list `{key: user.id, value: display_name || email}`; needleColumn = the delimited ids cell. Output: one row per input cell, tokens replaced via the map and re-joined in ORIGINAL order.

## Decisive source
pg.ts:53–59 — mapUnion builds `select ? as nc_p_key, ? as nc_p_value UNION ALL ...` per stack entry.
pg.ts:61–68 — the load-bearing comment: "`WITH ORDINALITY` keeps each id's position in the delimited cell so the string_agg below can pin the concatenation order. Without it the aggregate order is whatever the hash join emits — non-deterministic, and it shifts whenever the stack changes size/order, **silently corrupting User/CreatedBy sort & filter results**." unnest(string_to_array(??,'delimiter')) with ordinality as nc_t_arr(nc_p_needle, nc_p_ord).
pg.ts:73–85 — left join needle→stack on key, `string_agg(coalesce(value, key), ',' ORDER BY nc_p_ord)`, grouped by raw needle; unknown ids pass through as themselves (coalesce).
sqlite.ts:64–69 — same ordinality need met with json_each over a reconstructed JSON array (`json_each('["' || replace(needle,',','","') || '"]')`), carrying `.key` as position; GROUP_CONCAT(... ORDER BY nc_p_ord) at :75.
Base generic throws 'Not implemented' (generic.ts:197–204); group-by.ts:641–643 gates usage to pg/sqlite clientTypes only — other dialects fold N nested REPLACE() chains instead (:645–652).

## Flow / Invariant
The invariant that survives porting: **aggregate re-concatenation is order-unstable without an explicit positional key**. Any delimited-token rewrite (id→label) must thread token position through the join or results shuffle when the lookup table's cardinality/order changes. Also note the empty-stack short-circuit (:49–51 both dialects): no users ⇒ return needleColumn unchanged rather than joining against an empty map.

## Probe (direct test)
From repo root:
```
grep -c 'with ordinality' packages/nocodb/src/dbQueryClient/pg.ts                       # => 1 (:68)
grep -c 'order by nc_t_needle.nc_p_ord' packages/nocodb/src/dbQueryClient/pg.ts         # => 1 (:77)
grep -c 'json_each' packages/nocodb/src/dbQueryClient/sqlite.ts                         # => 2 (:58 comment + :66 SQL — grep -c counts lines carrying the token)
sed -n '197,204p' packages/nocodb/src/dbQueryClient/generic.ts | grep -c 'Not implemented'   # => 1
```

## Retrieve
```
codebase-memory-mcp cli search_graph '{"project":"mnt-hdd-utopia-inspo-platforms-nocodb","query":"replaceDelimitedWithKeyValue ordinality string_agg","limit":3,"detail":"compact"}'
```
→ generic stub 197-204 + PGDBQueryClient.replaceDelimitedWithKeyValue pg.ts 40-86.

## Verdict
**Adapt.** Port the ordinality discipline (pg) and json_each position trick (sqlite); for engines with neither, the REPLACE-chain fallback in group-by is the sanctioned degraded mode.
