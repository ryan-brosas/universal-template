<!-- capsule-v2 -->
# Composite hierarchical export ids — why every exported entity id is a `::`-joined ancestor chain instead of a bare uuid

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What do exported ids look like, who mints which segments, and what must an importer assume to resolve them?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:serializeModels` + `~/helpers/exportImportHelpers.ts:generateBaseIdMap/getEntityIdentifier`.

**Signature:** `generateBaseIdMap(context, source, idMap): Promise<Model[]>` seeds `${source.base_id}::${source.id}::${modelId}` per model; children then self-append.

**Data Shape:** depth-encoded chains joined by `::`: base→`{base_id}::`; source→`{base}::{source}`; model→`{base}::{source}::{model}`; view/hook/comment/permission→`{modelChain}::{childId}`; dashboard→`{base}::{dashId}` (2-segment); widget filters→prefixed with the WIDGET's mapped id; link filters→prefixed with the LINK COLUMN's mapped id.

### Decisive source
```ts
// seed (once per source): models get the 3-part prefix
if (!modelsMap.has(source.id)) modelsMap.set(source.id, await generateBaseIdMap(context, source, idMap));
// children append their own segment under the mapped parent
idMap.set(view.id,   `${idMap.get(model.id)}::${view.id}`);
idMap.set(hook.id,   `${idMap.get(hook.fk_model_id)}::${hook.id}`);
idMap.set(comment.id,`${idMap.get(model.id)}::${comment.id}`);
idMap.set(permission.id, `${idMap.get(permission.entity_id)}::${permission.id}`); // table OR FIELD entity
// late-bound target views (qr/barcode fk_target_view_id) mint on demand
const view = await View.get(context, v);
idMap.set(view.id, `${source.base_id}::${source.id}::${getEntityIdentifier(view.fk_model_id)}::${view.id}`);
```

**Flow:** `serializeModels` opens one `Map<string,string>` and registers entities as it walks them (models via generateBaseIdMap, then views/hooks/comments/permissions per model, dashboards in serializeDashboards). Every filter/sort/extras rewrite reads through idMap, so the serialized payload contains ONLY composite ids. The importer's `findWithIdentifier(idMap, …)` splits on the same separator to resolve ancestors.

**Invariant:** ids are POSITIONAL — segment count encodes entity kind (2 = base-scoped like dashboards, 3 = source-scoped like models, 4+ = model-scoped). A parent must be registered before any child appends to it, so walk order (model → its views/hooks → their filters) is load-bearing. Late-minted entries (fk_target_view_id) must use the same segment grammar as seeded ones or cross-references miss. Permissions reuse their ENTITY's mapped id as the prefix — field-level permissions point at mapped column ids, not the table.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:260-265` (per-source seeding), `:330-341` (late fk_target_view_id mint), `:443-445`/`:643`/`:706`/`:742-746` (child appends), plus `exportImportHelpers.ts` for `getEntityIdentifier`. Consumer proof: `duplicate.processor.ts` resolves these ids during import phases (see export-idmap capsule).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "generateBaseIdMap getEntityIdentifier clearPrefix idMap", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt positional composite ids as the portable cross-instance reference format (self-describing ancestry, collision-free across sources); adapt separator/segment count to host; omit workspace-integration preservation keys unless porting those. Coverage caveat: no in-repo unit tests; source-grounded.
