<!-- capsule-v2 -->
# Legacy extract funnel — how does the v1 route family resolve base/source when no baseId param exists, and why does it track a separate tableIdToCheck?

**Source:** nocodb (Sustainable Use License) `develop@640fe3b06f`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-nocodb`. **Question:** What does `legacyExtractIds` do differently from the modern funnel, and what is `ncTableId` for?

## Dual-funnel with deferred table-visibility pin
**Path/Symbol:** `packages/nocodb/src/middlewares/extract-ids/extract-ids.middleware.ts:ExtractIdsMiddleware.legacyExtractIds` (:476–:1053).
**Signature:** `protected async legacyExtractIds(req)` — class-protected so EE subclasses extend via `additionalValidation`, not by rewriting the funnel.
**Data Shape:** same `req.nc*` outputs as `use()` PLUS `tableIdToCheck: string | null` → stored at :1050–:1052 as `req.context.ncTableId` for the ACL middleware's table-visibility check; context additionally carries `org_id` and `timezone` (from `whereTz` query).

### Decisive source
```ts
let tableIdToCheck: string | null = null; // Store table ID for permission check at the end
// ... 14 assignment sites across model/view/hook/column/filter/sort/section branches ...
if (tableIdToCheck) {
  req.context.ncTableId = tableIdToCheck;
}
```
(:484, :562–:871, :1050–:1052)

**Flow:** identical else-if ladder over `params.*` only (no query fallbacks), but each branch ALSO records the owning table (`view.fk_model_id`, `column.fk_model_id`, hook/comment paths, comments POST body `fk_model_id`, `/auth/user/me` query params) → then a workspace-resolution cascade (baseId → re-fetch Base → `params.workspaceId` → `workspaceOrOrgId` → base-create body `fk_workspace_id` → integrations-list `query.baseId` validated against resolved workspace) → late view recovery: if no branch consumed `viewId|filterId|sortId` from QUERY params, resolve them NOW but ONLY attach when `instanceof View` (:991–:1014) → default-workspace fallback gated on `req.ncAclScope === 'workspace'|'base'` (:1021–:1029) → context build.
**Invariant:** `ncTableId` must be the pk-bearing MODEL id of the entity the route acts through — it powers table-level visibility ACL downstream; resolving it from an alias or leaving it unset fails visibility silently. The three `instanceof View` guards exist because `View.get` can return a Model row (viewId||Model.get fallback) and a Model must NOT trigger personal-view gates.
**Probe:** `cd packages/nocodb && grep -c "tableIdToCheck = " src/middlewares/extract-ids/extract-ids.middleware.ts` (=14 assignments) vs `grep -c "req.context.ncTableId" src/middlewares/extract-ids/extract-ids.middleware.ts` (=1 store) and `grep -c "instanceof View" src/middlewares/extract-ids/extract-ids.middleware.ts` (=3).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-nocodb", query: "legacyExtractIds tableIdToCheck ncTableId instanceof View", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the deferred-table-pin pattern (identity first, permission target pinned once) and the instanceof guard before ACL-affecting attachment; adapt which entities carry fk_model_id to your schema; omit the v1 comment/audit special-case routes unless porting the legacy API surface. Coverage caveat: no dedicated spec; counts verified against source at pin.
