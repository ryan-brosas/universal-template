<!-- capsule-v2 -->
# DatasService grouped-list dual path — why does PostgreSQL get a no-nocoExecute fast path only when `opt=true`?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does one endpoint serve grouped (kanban-style) listings across SQL dialects without forking the response contract?

## DatasService.getGroupedDataList
**Path/Symbol:** `packages/nocodb/src/services/datas.service.ts:getGroupedDataList` (:495-622); pg branch gate at :509-511.
**Signature:** `getGroupedDataList(context, { model, view?, query, columnId })` — `view` is OPTIONAL: "view-less callers (interface pages) scope via query.filterArrJson" (:499-500).
**Data Shape:** Both branches return `[{ key, value: PagedResponseImpl }]`; per-group count comes from `groupedListCount` matched by `key`, defaulting to 0 (`countItem.key === item.key)?.count ?? 0`).

### Decisive source
```ts
// :507-511 — the dialect+opt-in gate
const source = await Source.get(context, model.source_id);
// Use singleQueryGroupedList for PostgreSQL to avoid nocoExecute
// It handles nested columns/rollups directly in SQL
if (source.type === 'pg' && param.query?.opt === 'true') {
```
```ts
// pg branch (:540-563) — rows come back render-ready; wrap in PagedResponse
const [groupedData, countArr] = await Promise.all([
  await baseModel.groupedList({ ...listArgs, groupColumnId: param.columnId }),
  baseModel.groupedListCount({ ...listArgs, groupColumnId: param.columnId }),
]);
return groupedData.map((item) => {
  const count = countArr.find((c) => c.key === item.key)?.count ?? 0;
  return { ...item, value: new PagedResponseImpl(item.value, { ...query, count }) };
});

// fallback branch (:594-621) — raw groups must pass through the AST projection
let data = [];
const groupedData = await baseModel.groupedList({ ..., includeRowColorColumns..., includeButtonFilterColumns... });
data = await nocoExecute({ key: 1, value: ast }, groupedData, {}, listArgs);
const countArr = await baseModel.groupedListCount(...);
data = data.map((item) => { item.value = new PagedResponseImpl(item.value, {...query, count}); return item; });
```

**Flow:** source lookup → `source.type === 'pg' && query.opt === 'true'` ? single-query path (AST used ONLY to derive dependencyFields, nested cols/rollups resolved inside SQL) : classic path (`nocoExecute({ key: 1, value: ast }, ...)`) → per-key count join with `?? 0` → PagedResponse per group. Note the pg branch drops `includeRowColorColumns`/`includeButtonFilterColumns` from its groupedList call args while the fallback forwards them — an intentional capability gap of the optimized SQL path at this pin.
**Invariant:** The response CONTRACT is identical on both paths; what differs is where projection happens (SQL vs AST). Porting hazard: enabling a "fast path" that skips your projection layer must produce byte-identical cells or you fork behavior per customer DB engine — hence upstream gates it behind BOTH dialect and an explicit opt-in query flag. Count-join by group key is total (missing count ⇒ 0), never throws.
**Probe:** Runner blocked at this pin. Deterministic probe: grep confirms exactly one `'pg' && param.query?.opt === 'true'` conjunction in src; two `groupedListCount` call sites (:545/:604) each paired with exactly one `groupedList`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "groupedList groupedListCount opt", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dialect-gated optimization behind an explicit opt-in with identical response contracts. Adapt the gate (your dialect + capability probe). Omit the color/button-column forwarding if those features don't exist in your port.
