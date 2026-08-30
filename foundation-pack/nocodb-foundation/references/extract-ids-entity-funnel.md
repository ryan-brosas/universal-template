<!-- capsule-v2 -->
# ExtractIds entity funnel — how does one middleware turn arbitrary route params into an authenticated NcContext before any controller runs?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06fb26c9d000e2258477001c0d5e62c73`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** How does the request pipeline resolve base/source/context from ANY of ~25 id params, and what does a porter get wrong about the resolution order?

## Param-precedence identity funnel
**Path/Symbol:** `packages/nocodb/src/middlewares/extract-ids/extract-ids.middleware.ts:ExtractIdsMiddleware.use` (:109–:457).
**Signature:** `async use(req, res): Promise<any>` — also implements `CanActivate.canActivate(context)` (:460–:466) so controllers without the express-layer registration still run it.
**Data Shape:** reads `req.params`/`req.query` pairwise (`params.tableId || params.modelId || params.tableName || query.tableId`, …), writes `req.ncBaseId/ncWorkspaceId/ncSourceId/ncApiVersion/ncSocketId/ncTabId` plus the composed `req.context {workspace_id, base_id, api_version, socket_id, tab_id, nc_site_url, permissions: []}`.

### Decisive source
```ts
const mcpTokenId = params.mcpTokenId || query.mcpTokenId;
const integrationId = params.integrationId || query.integrationId;
const tableId = params.tableId || params.modelId || params.tableName || query.tableId;
const viewId = params.viewId || params.viewName || query.viewId;
// ...
if (mcpTokenId) { /* MCPToken.get(FULL_BYPASS ctx) → RE-DERIVES ncBaseId+ncWorkspaceId from token row */ }
else if (integrationId) { Integration.get(...) }
else if (tableId) { Model.get(context, tableId); req.ncSourceId = model.source_id; }
else if (viewId) { View.get(...) || Model.get(...); req.ncSourceId = view.source_id; }
```
(:151–:230)

**Flow:** URL-prefix sniff `/api/v3|v2|v1` sets `ncApiVersion` → internal-API escape (`/api/v2/internal` + `baseId === 'nc'`) skips base resolution entirely → base param loads Base (404 funnel otherwise) → exactly ONE branch of a strict else-if ladder resolves the primary entity (mcpToken > integration > table > view > typed-view ids > publicDataUuid/sharedViewUuid/sharedBaseUuid > hook > buttonCol > rowColorCondition > *ViewColumn > column > filter/filterParent > widget > section/baseSection > sort > sync > extension), each 404-ing through typed `NcError.*notFound` → share uuids flip `req.context.is_public` + `access_source` → falls back to `legacyExtractIds(req)` when no baseId param exists → `additionalValidation()` hook (EE override point) → `next()`.
**Invariant:** the ladder is FIRST-MATCH-WINS by design — a route carrying both tableId and filterId resolves identity from the TABLE, never the filter; adding a new id param means inserting it at the right precedence slot, not appending. Every miss must land in the 404 funnel BEFORE handlers run (the `baseSectionId` branch exists ONLY to 404 early — it pins no source).
**Probe:** `cd packages/nocodb && grep -c "NotFound(" src/middlewares/extract-ids/extract-ids.middleware.ts` (=54 typed 404 sites) and `grep -c "else if (" src/middlewares/extract-ids/extract-ids.middleware.ts` (=59 ladder arms across both funnels).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "ExtractIdsMiddleware use legacyExtractIds NcError tableNotFound", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-funnel param precedence + eager 404-before-handler discipline and the `req.context` shape; adapt the id-param vocabulary and error taxonomy to your routes; omit the v1 legacy funnel only if you have no legacy route surface. Coverage caveat: no upstream unit spec imports this middleware (controller specs are construction-only); source-grounded probes stand in.
