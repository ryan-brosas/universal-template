<!-- capsule-v2 -->
# MSSQL OFFSET/FETCH needs ORDER BY even when nothing sorts — the (SELECT NULL) no-op key

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** Why does a sortless group-by page break on T-SQL only, and what's the minimal legal fix?

## Mandatory ORDER BY for OFFSET/FETCH
**Path/Symbol:** `packages/nocodb/src/db/BaseModelSqlv2/group-by.ts:list` :691-707 (+ gate flag at :585-587).
**Signature:** applied AFTER the sort loop, ONLY on the mssql branch, before returning `execAndParse(outerQb)` directly.
**Data Shape:** constant expression `(SELECT NULL)` appended as final order key.

### Decisive source
```ts
// :691-703 — the comment is the whole contract:
// T-SQL requires an ORDER BY whenever OFFSET/FETCH pagination is present
// (applyPaginate always sets .offset()). The sort loop above only emits an
// ORDER BY when a sort targets a grouped column, so a sortless group-by —
// or one whose sorts don't match a group key — would reach page 2+ with
// OFFSET/FETCH and no ORDER BY → "Invalid usage of NEXT in FETCH".
if (baseModel.isMssql) {
  if (!NC_DISABLE_GROUP_BY_LIMIT) {
    outerQb.orderByRaw('(SELECT NULL)');
  }
  // T-SQL forbids wrapping a CTE in a derived table → skip __nc_group_alias wrap
  return await baseModel.execAndParse(outerQb);
}
```
`NC_DISABLE_GROUP_BY_LIMIT` = `process.env.NC_DISABLE_GROUP_BY_LIMIT === 'true' || false` (`packages/nocodb/src/utils/nc-config/constants.ts:100-101`) gates BOTH pagination (:585-587) and this no-op key.

**Flow:** sorts loop emits keys only for grouped columns → mssql always appends the constant key last → constant-for-every-row ⇒ never reorders, just satisfies the syntax rule (mirrors `ensurePaginationOrderBy` in the EE single-query client).
**Invariant:** (1) The fix must be a CONSTANT expression — any real column here would impose an unintended total order. (2) It must come AFTER user sorts so it can never dominate them. (3) Non-mssql engines tolerate OFFSET without ORDER BY — do not apply globally.
**Probe:** No unit tests upstream. Deterministic probe: rendered mssql SQL for a sortless paged group-by ends with `order by (SELECT NULL)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "ensurePaginationOrderBy NC_DISABLE_GROUP_BY_LIMIT", limit: 5 });
// nocodb.packages.nocodb.src.db.BaseModelSqlv2.group-by.list Function group-by.ts 109-724 (:691-703)
```

## Verdict
Adopt the trailing constant-key rule keyed to OFFSET/FETCH engines; adapt env gate naming to host config. Caveat: no direct tests at pin; graph range verified live.
