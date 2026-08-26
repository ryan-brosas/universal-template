<!-- capsule-v2 -->
# Per-lookup top-N via pk-IN — why is LIMIT expressed as a correlated pk subquery instead of LIMIT on the query?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How do display/filter/formula consumers share ONE "top-N related rows" contract, and how does "last N" keep natural order?

## lookupSortLimit choke point
**Path/Symbol:** `packages/nocodb/src/db/lookupSortLimit.ts:loadLookupSortAndLimit` (:34-67), `applyLookupPkInLimit` (:146-211), `applyNestedLookupLevelLimit`/`buildNestedLookupLevelLimit` (:224-320), `applyLookupSortLimitToQb` (:82-131), `applyLookupFilterWindowLimit` (:345-414).
**Signature:** `loadLookupSortAndLimit(context, column): Promise<{sorts: Sort[]; limitVal: number; takeLast: boolean; hasConfig: boolean}>`; config lives in Sort rows (`fk_lookup_col_id`) + `column.meta.lookup_limit {type:'first'|'last', value}`.
**Data Shape:** PG-only feature (callers gate); EE-gated (`isLookupSortLimitLicensed`, CE-stubbed false) — unlicensed reports `hasConfig:false` so EVERY consumer short-circuits identically.

### Decisive source
```ts
// :133-141 + :168-210 — the WHY, verbatim intent: unlike ORDER BY/LIMIT on the
// query directly, a correlated pk-IN composes with whatever the consumer does
// afterwards (STRING_AGG in formula, json_agg for sort key, EXISTS in filter):
//   ... AND <alias>.<pk> IN (SELECT <pk> FROM <same rows>
//                            ORDER BY <sortkey> LIMIT n)
const inner = qb.clone();                 // clone REUSES the relation correlation
if (typeof inner.clearSelect === 'function') inner.clearSelect();
for (const pk of pks) inner.select(`${alias}.${pk.column_name}`);
const effective = takeLast
  ? sorts.map(s => new Sort({...s, direction: s.direction === 'desc' ? 'asc' : 'desc'}))
  : sorts;                                // "last N" = FLIP the sort, take head
for (const s of effective) inner.orderBy(`${alias}.${col.column_name}`, dir);
for (const pk of pks)
  inner.orderBy(`${alias}.${pk.column_name}`, takeLast ? 'desc' : 'asc'); // tiebreak
inner.limit(limitVal);
pks.length === 1 ? qb.whereIn(`${alias}.${pks[0].column_name}`, inner)
                 : qb.whereIn(pks.map(pk => `${alias}.${pk.column_name}`), inner);

// :101-117 — last-N presentation: pk-IN picks the tail SET, outer re-sort by the
// UN-flipped sort restores natural order; no outer LIMIT (pk-IN already fixed set)
```

**Flow:** load config (empty ⇒ skip license check entirely; unlicensed ⇒ empty) → consumer-specific application: display path sorts+limits directly on the row query (`applyLookupSortLimitToQb`: first-N = sort then LIMIT with pk-asc appended as deterministic final term); nested levels build an explicit correlation from level columns (`__nc_lk_nlvl` alias, single-PK only, deferred sync applier for the filter path where the qb doesn't exist yet); FILTER path ranks base rows with `ROW_NUMBER() OVER (PARTITION BY fk ORDER BY sortkey)` keeping rn<=N (`applyLookupFilterWindowLimit`, `__nc_lk_win` aliases) because the filter's qb is a GLOBAL `parent IN (qb)` set where per-parent LIMIT cannot be expressed.
**Invariant:** (1) The pk-IN must CLONE the consumer's qb so the exact relation correlation carries over — rebuilding it drifts. (2) The final ORDER BY term inside the limited set is ALWAYS the pk (flipped for last-N): boundary ties resolve identically across display/filter/formula/list-vs-count. (3) "Last N" never reverses presentation — flipped sort selects the tail, un-flipped outer sort displays it. (4) Filter-window ranking is deliberately UNCORRELATED to the outer parent set (accepted v1 perf cost, documented).
**Probe:** No unit tests upstream. Deterministic probe: limit=3 over [9..1] desc renders `pk IN (SELECT pk … ORDER BY val DESC, pk DESC LIMIT 3)` selecting {9,8,7}; takeLast with asc sort selects the TAIL but presents ascending.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "applyLookupPkInLimit buildNestedLookupLevelLimit", limit: 5 });
// applyLookupPkInLimit 146-211, buildNestedLookupLevelLimit 248-320
```

## Verdict
Adopt the pk-IN-instead-of-LIMIT pattern, clone-for-correlation rule, pk-tiebreaker discipline, and the flip-sort-take-head trick. Adapt the EE license gate to your plan system. Omit nothing else portable. Caveat: no direct tests at pin; graph ranges verified live.
