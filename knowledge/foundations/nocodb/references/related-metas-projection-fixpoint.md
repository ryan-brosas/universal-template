<!-- capsule-v2 -->
# Related-meta projection — why must the schema a share exposes agree with the data path's pkAndPvOnly?

**Source:** NocoDB Sustainable Use License `develop@f7513664`; Codebase Memory `nocodb`. **Question:** How does an anonymous shared-view consumer get linked-table metadata without leaking hidden foreign columns — and why is a fixpoint loop required?

## extractRelatedMetas + projectRelatedMetas
**Path/Symbol:** `packages/nocodb/src/services/public-metas.service.ts:extractRelatedMetas` (:226-251), `extractLTARRelatedMetas` (:253-289), `filterIfLimitedAccess` (:291-308), `extractLookupRelatedMetas` (:310-372); helpers in `packages/nocodb/src/helpers/relatedMetaProjection.ts` (213L whole).
**Signature:** `projectRelatedMetas(relatedMetas: Record<string, Model>, baseColumns)` mutates the MAP, replaces each Model with a projected COPY; `projectRelatedModelColumns(related: Model, neededColIds: Set<string>): Model`.
**Data Shape:** Keep-set seed = pk(s) + pv + ids pulled by allowed lookups/rollups (`fk_lookup_column_id`, `fk_rollup_column_id`) + link display column (`fk_display_value_column_id`) + link structural four (`fk_child_column_id`, `fk_parent_column_id`, `fk_mm_child_column_id`, `fk_mm_parent_column_id`).

### Decisive source
```ts
// public-metas.service.ts :170-177 (comment quoted):
// `extractRelatedMetas` above attaches each related/junction table's FULL
// column set, so an anonymous consumer would get the names, types and select
// options of columns the share never exposes. Project down to what the DATA
// path returns under `pkAndPvOnly` — the two must agree, or the frontend
// renders fields the API refuses to return.
if (isSharedViewAccess(context)) {
  projectRelatedMetas(relatedMetas, view.model.columns);
}
```
```ts
// relatedMetaProjection.ts :176-186 — copies, never in-place edits:
// Returns a COPY — the underlying Model is cache-shared, so its
// `columns`/`columnsById` must never be mutated in place.
return Object.assign(Object.create(Object.getPrototypeOf(related)), related, {
  columns, columnsById,
  columnsHash: undefined,
});
```
```ts
// :200-206 — why one pass is wrong:
// The needed-column set must reach a FIXPOINT across the chain: base pulls
// `B.L2`, and `L2` itself pulls a column on a deeper table `C`, so a single
// base-only pass would trim `C` to pk+pv and strip the chain's terminal
// column. Hence: re-collect from every KEPT related column until nothing new appears.
const RELATED_PROJECTION_MAX_PASSES = 6;   // safety bound; chains are short
```
```ts
// sameModelColumnDeps :96-135 — generic dependency discovery:
// any `colOptions`/`meta` value that IS a column id on this same model counts,
// plus formula column-id references embedded in the formula string. Cross-table
// references ... naturally excluded because they aren't in `sameModelIds`.
```

**Flow:** per surviving column → LTAR ⇒ related model (+ junction via mmContext) loaded with `getRelContext`; Lookup ⇒ relation col + looked-up col metas via refContext then RECURSES into the looked-up column (:368-371) → null entries pruned (:165-168) → shared-access projection to fixpoint → per-table `filterIfLimitedAccess` trims to pk/pv when visibility lacks default access (complementary coarse gate). Formula deps found by substring-scanning the formula string for known same-model ids.
**Invariant:** (1) Schema/data agreement is the security property: metadata wider than the data envelope leaks names/options of never-returnable columns. (2) Models are cache-shared ⇒ replace-with-copy, never mutate; prototype preserved via `Object.create(Object.getPrototypeOf(...))`. (3) The dependency closure must be transitive across link chains or deep shares lose renderable cells. (4) Recursion into looked-up columns means lookup-of-lookup chains pull every intermediate table's meta.
**Probe:** Runner blocked at this pin. Deterministic probe: grep confirms exactly one `RELATED_PROJECTION_MAX_PASSES` (= 6) and one `isSharedViewAccess(context)` gate inside viewMetaGet; projection helper exports exactly three functions (`collectRelatedNeededColumnIds`, `projectRelatedModelColumns`, `projectRelatedMetas`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "projectRelatedMetas collectRelatedNeededColumnIds", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt metadata-to-data-envelope agreement as an invariant with fixpoint closure over virtual-column dependencies. Adapt the keep-set fields to your column model. Omit the visibility-limited trim if you have no per-table visibility ACL.
