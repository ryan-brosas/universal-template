<!-- capsule-v2 -->
# Export service identity map — how do serializeModels/importModels keep a source→dest id map that every later import step can trust?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What is the idMap contract shared by export/import services and the duplicate/migrate processors?

## idMap threading through serialize/import pairs
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.serializeModels`; `import.service.ts:ImportService.importModels` (returns `Map<string,string>`); consumers `duplicate.processor.ts:153-157, 249-303, 988-1088`.
**Signature:** `serializeModels(context, {modelIds, ...options}): Promise<{serializedModels; idMap: Map<string,string>}>` (source→source); `importModels(targetContext, {data, externalModels?, columnWebhookManager?, isDuplicateOperation}): Promise<Map<string,string>>` (source→dest).
**Data Shape:** keys = source entity ids; values = destination ids; dashboards/workflows/interfaces IMPORTS take an existing idMap and return an EXTENDED one.

### Decisive source
```ts
const { serializedModels: exportedModels, idMap: exportModelMap } =
  await this.exportService.serializeModels(context, { modelIds: models.map((m) => m.id), ...options });
...
let idMap = await this.importService.importModels(targetContext, { data: exportedModels, isDuplicateOperation: true });
if (exportedDashboards?.length) {
  idMap = await this.importService.importDashboards(targetContext, { ..., idMap });   // extends
}
if (exportedWorkflows?.length) {
  idMap = await this.importService.importWorkflows(targetContext, { ..., idMap });    // extends
}
```

**Flow:** schema serialization produces its own within-source alias map; model import then creates real destinations and yields the canonical cross-context map. Every subsequent importer (dashboards → workflows → interfaces) receives the accumulated map, rewrites its internal references, and appends new entries. Data streaming resolves per-row values through `findWithIdentifier(idMap, sourceModel.id)`.
**Invariant:** the map is write-once per entity type but EXTENDED across phases — later importers must receive and RETURN it, or their references dangle. Same-id duplication (base restore) uses the identity map (source id == dest id) so external-model backfill can skip translation. Serialization order must match reference direction (interfaces last — see duplicate-compensation capsule).
**Probe:** no unit test upstream. Source-grounded probe: `duplicate.processor.ts:249-256` vs `:277-284` — first import creates, later imports extend; `findWithIdentifier` usage at `:547`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "serializeModels importModels idMap findWithIdentifier", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt a single accumulating id-map passed into and returned from every phase importer; adapt to your ORM's id types; omit webhook-manager/EE flags unless porting those subsystems. Coverage caveat: no in-repo tests; source-grounded.
