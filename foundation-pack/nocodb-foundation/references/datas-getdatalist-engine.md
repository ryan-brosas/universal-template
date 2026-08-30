<!-- capsule-v2 -->
# DatasService getDataList engine — why do count and list run concurrently, and which errors rethrow?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** What is the exact shape of the shared read engine every alias route funnels into?

## DatasService.getDataList
**Path/Symbol:** `packages/nocodb/src/services/datas.service.ts:getDataList` (:231-337).
**Signature:** `getDataList(context, { model, view?, query, baseModel?, throwErrorIfInvalidParams?, ignoreViewFilterAndSort? = false, ignorePagination?, limitOverride?, customConditions?: Filter[], getHiddenColumns?, apiVersion?, includeSortAndFilterColumns? = false, includeRowColorColumns?, includeButtonFilterColumns?, skipSortBasedOnOrderCol? = false, extractOrderColumn? })` — 16 knobs, all optional except model+query.
**Data Shape:** `listArgs` starts as `dependencyFields`; then `listArgs.filterArr = JSON.parse(listArgs.filterArrJson)` and `sortArrJson`→`sortArr` inside **empty-catch try blocks** (malformed JSON silently ignored, :290-295); `customConditions` attached verbatim (:297).

### Decisive source
```ts
const baseModel = param.baseModel || (await Model.getBaseModelSQL(...));  // caller may inject :265-272
const { ast, dependencyFields } = await getAst(context, {
  model, query, view,
  throwErrorIfInvalidParams: param.throwErrorIfInvalidParams,
  ...
  skipSubstitutingColumnIds:
    query?.[QUERY_STRING_FIELD_ID_ON_RESULT] === 'true',   // :285-286 — read from RAW query
});
...
// v3 twin reads the CONTEXT version, not the query (:313-315):
skipSubstitutingColumnIds:
  context.api_version === NcApiVersion.V3 &&
  query?.[QUERY_STRING_FIELD_ID_ON_RESULT] === 'true',
...
const [count, data] = await Promise.all([
  baseModel.count(listArgs, false, param.throwErrorIfInvalidParams),
  (async () => {
    let data = [];
    try {
      data = await nocoExecute(ast, await baseModel.list({...}), {}, listArgs);
    } catch (e) {
      if (e instanceof NcBaseError || e instanceof NcSDKErrorV2) throw e;
      this.logger.error(`Error fetching data: ${e?.message}`, e?.stack);
      NcError.get(context).internalServerError('Please check server log for more details');
    }
    return data;
  })(),
]);
return new PagedResponseImpl(data, {
  ...query,
  ...(param.limitOverride ? { limitOverride: param.limitOverride } : {}),
  count,
});
```

**Flow:** optional injected baseModel → getAst (AST + dependencyFields in one pass) → silent JSON coercion of filter/sort → parallel `Promise.all(count, list+nocoExecute)` → typed errors rethrow (`NcBaseError`, `NcSDKErrorV2`), everything else logged + generic internalServerError (stack never leaves the process) → PagedResponse with count merged AFTER the query spread.
**Invariant:** (1) The error funnel is a TYPE check, not a message check — port your own typed errors into that branch or anonymous clients lose actionable 4xxs. (2) `QUERY_STRING_FIELD_ID_ON_RESULT` is consulted from raw `query` for the AST but AND-ed with `context.api_version === V3` for the SQL fetch — a porter who unifies them to one site changes behavior on one API version. (3) Count runs even when list fails (parallel); failure of either rejects the whole response. (4) `limitOverride` must be spread AFTER query or a client-supplied `limitOverride` query key could fight it.
**Probe:** Runner blocked at this pin. Deterministic probe: grep confirms exactly one `Promise.all([baseModel.count` in the file; one `NcSDKErrorV2` rethrow site (:323); PagedResponse construction sites all place `count` last (:332-336, :558-561, :614-617).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "getDataList Promise.all nocoExecute", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the parallel-count read engine + typed-error funnel + post-spread override pattern wholesale — it is the shape of every list endpoint. Adapt knob names. Omit `extractOrderColumn`/row-color/button-filter columns if your views lack those features.
