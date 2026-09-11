<!-- capsule-v2 -->
# Lookup aggregation compiler — how do BT/HM/MM lookups join, when is aggregation SKIPPED, and what does each dialect aggregate to?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does generateLookupSelectQuery build the nested-join subquery and pick the per-dialect aggregate — and why does an all-BT lookup skip aggregation entirely?

## Nested lookup builder + dialect aggregators
**Path/Symbol:** `packages/nocodb/src/db/generateLookupSelectQuery.ts:generateLookupSelectQuery` (:128-920); display resolution helpers :39-121.
**Signature:** `generateLookupSelectQuery({column, baseModelSqlv2, alias, model, getAlias = getAliasGenerator('__lk_slt_'), isAggregation?}): Promise<QueryWithCte>` where QueryWithCte = `{builder, applyCte}` (applyCte currently a no-op closure — keep the slot).
**Data Shape:** Works for Lookup AND bare LTAR/Links columns (LTAR uses the target table's display value). Failure = `{builder: NC_ERROR_SENTINEL, applyCte: noop}` (broken colOptions, missing relation col, missing lookup col). OO relations are FOLDED at entry: `relation.meta?.bt ? BELONGS_TO : HAS_MANY` (:211-215).

### Decisive source
```ts
// :763-769 — ALL-BT chains need no aggregation: a belongs-to join yields
// exactly ONE row per parent row, so the plain correlated select IS the cell
if (isBtLookup) return { builder: selectQb, applyCte };

// :773-799 — pg: json_agg over the SUBQUERY-aliased rows, cast to text
return { builder: knex.select(knex.raw('json_agg(??)::text', [lookupColumn.id]))
           .from(selectQb.as(subQueryAlias)), applyCte };
// mm link-order default (:375-383): junction Order column selected as
// '__nc_lorder' and json_agg(col ORDER BY __nc_lorder)::text — but ONLY
// when the lookup has NO own sort/limit config (explicit config wins)

// :818-826 mysql: cast(JSON_ARRAYAGG(col) as NCHAR)
// :839-852 sqlite: group_concat(col, '___')
// :853-886 mssql: JSON_QUERY('[' + COALESCE(STRING_AGG('"' +
//   STRING_ESCAPE(RTRIM(CAST(col AS NVARCHAR(MAX))),'json') + '"', ','), '') + ']')
//   — RTRIM strips CHAR padding; everything stringified (numeric → "1");
//   COALESCE prevents STRING_AGG's NULL on empty set from rendering [NULL]
// :887-912 oracle: JSON_ARRAYAGG(col NULL ON NULL RETURNING VARCHAR2(4000))
//   — NULL ON NULL keeps nulls for pg parity (default is ABSENT ON NULL);
//   CLOB inputs pre-shortened DBMS_LOB.SUBSTR(col,2000,1) or the agg rejects LOB
```

**Flow:** resolve relation ⇒ fold OO → per-shape correlated base query with soft-delete filter (BT parent-side / HM child-side / MM referenced-side via junction innerJoin) → btLikeV2-junction ⇒ LIMIT 1 → walk `lookupColumn` chain in a WHILE loop: each nesting level mints a new alias and ADDS a JOIN (BT joins parent on prevAlias.fk; HM joins child; MM double-joins junction+parent), PG-only per-level top-N via pk-IN (`applyLookupPkInLimit` outer / `applyNestedLookupLevelLimit` inner) → terminal value select by uidt (Links/Rollup→genRollupSelectv2 wrapped `(…)`, Formula→formulaQueryBuilderv2 aliased via getAs, DateTime family→baseModel.selectObject, Attachment REJECTED unless isAggregation, default `prevAlias.col AS col.id`) → if any level was non-BT, wrap in the dialect aggregator above.
**Invariant:** (1) Soft-delete exclusion happens on EVERY joined level, not just the first. (2) The bt-vs-aggregate fork is decided by whether ANY level was non-BT (`isBtLookup=false` on first HM/MM-nonV2) — not per level. (3) Display-value fallback chain: LTAR override column → PV → cols[0]; PK-as-subfield allowed ONLY for literal `'id'` and falls back to PV if hidden in fk_target_view_id (view-visibility leak guard). (4) QrCode/Barcode unwrap to their value column before selecting.
**Probe:** No unit tests upstream. Deterministic probe: single-level BT lookup renders a flat correlated SELECT with NO wrapper; same shape over HM renders `SELECT json_agg(id)::text FROM (…correlated…) __lk_slt_x`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "generateLookupSelectQuery getDisplayValueOfRefTable", limit: 5 });
// generateLookupSelectQuery 128-920, getDisplayValueOfRefTable 39-63, getRefTableColumnForFilter 80-121
```

## Verdict
Adopt the while-loop nested-join walker, all-BT-skip aggregation, per-dialect aggregate shapes (incl. MSSQL manual JSON array and Oracle NULL ON NULL), soft-delete-on-every-level, and the id-only-PK filter rule. Adapt alias generator + sentinel constant. Caveat: no direct tests at pin; graph ranges verified live.
