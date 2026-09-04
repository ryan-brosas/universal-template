<!-- capsule-v2 -->
# sortV2 orchestrator — which sort keys are unsortable per dialect and how are they cast back into comparability?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** Why does the sort orchestrator intercept LOB columns before delegating to field handlers, and what are the exact casts?

## Orchestrator-level LOB rescue + delegation
**Path/Symbol:** `packages/nocodb/src/db/sortV2.ts:sortV2` (:9-106).
**Signature:** `sortV2(baseModelSqlv2, sortList: Sort[], qb, alias?, throwErrorIfInvalid = false): Promise<void>` — mutates qb in place; NO deferred result (unlike conditionV2).
**Data Shape:** Accepts `Sort | SortType` (wraps plain objects via `new Sort(_sort)`); skips `enabled === false || enabled === 0` entries; missing column errors only when `throwErrorIfInvalid`, else `continue`. Null placement derives from direction: `desc ⇒ NULLS LAST`, else `NULLS FIRST`.

### Decisive source
```ts
// :29-37 — T-SQL refuses ORDER BY on text/ntext/image/xml. Cast to a BOUNDED
// NVARCHAR(4000), NOT MAX: a MAX/LOB sort key still over-estimates the memory
// grant, spills to tempdb (seconds not ms). 4000 chars = 8000 bytes.
const mssqlUnsortableDt = new Set(['text', 'ntext', 'image', 'xml']);
qb.orderBy(sanitize(knex.raw(`CAST(?? AS NVARCHAR(${MSSQL_SORT_KEY_WIDTH}))`,
  [column.column_name])), direction, nulls);

// :39-44 — Oracle refuses LOBs as comparison keys (ORA-22848); LongText/JSON/
// Attachment store as CLOB there. DBMS_LOB.SUBSTR returns VARCHAR2 for CLOB
// (NVARCHAR2 for NCLOB) — sortable and under the 4000-byte cap.
const oracleUnsortableDt = new Set(['clob', 'nclob']);
qb.orderByRaw(sanitize(knex.raw(
  `DBMS_LOB.SUBSTR(??, 2000, 1) ${direction} NULLS ${nulls}`, [column.column_name])));

// :98-104 — everything else delegates; handlers receive the precomputed nulls
await fieldHandler.applySort(qb, column, direction, { alias, nulls, context, knex, baseModel });
```

**Flow:** per sort entry: skip disabled → resolve column (`getRefColumnIfAlias`) → MSSQL dt in set? bounded NVARCHAR cast branch → Oracle dt clob/nclob? DBMS_LOB.SUBSTR raw branch → otherwise FieldHandler.applySort with `{alias, nulls}` so per-type handlers keep consistent NULL placement.
**Invariant:** (1) The LOB check is keyed on `column.dt` (physical type), NOT uidt — that's WHY it lives in the orchestrator: per-type handlers can't see the underlying dt without repeating the check. (2) Prefix-truncation trade-off is accepted and documented: rows sharing a 4000/2000-char prefix sort undefined among themselves — fine for a display sort key, fatal if reused as an equality key. (3) Direction→nulls mapping is fixed at ONE place and passed down.
**Probe:** No unit tests upstream. Deterministic probe: sorting a pg text column renders plain ORDER BY; same column as MSSQL `text` renders `CAST(col AS NVARCHAR(4000)) ASC NULLS FIRST`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "sortV2", limit: 5 });
// nocodb.packages.nocodb.src.db.sortV2.sortV2 Function sortV2.ts 9-106
```

## Verdict
Adopt the dt-keyed orchestrator interception, bounded-cast rationale (4000 NVARCHAR / 2000 SUBSTR), and single-source nulls mapping. Adapt handler delegation shape. Caveat: no direct tests at pin; graph range verified live.
