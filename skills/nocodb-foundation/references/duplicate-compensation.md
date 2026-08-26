<!-- capsule-v2 -->
# Duplicate compensation — when a base/table duplication fails midway, how is the half-built copy cleaned up so users never see zombie bases?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What does the duplicate processor undo on failure, and in what order does it serialize/import?

## serialize→import ordering + soft-delete rollback
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/export-import/duplicate.processor.ts:DuplicateProcessor.duplicateBaseJob/duplicateModel` (81-373, 440-633).
**Signature:** `duplicateBaseJob({sourceBase, targetBase, dataSource, req, context, options, operation})`; `duplicateModel(job): Promise<{id}>`.
**Data Shape:** `idMap: Map<sourceId, destId>` threaded through every import call and returned/merged by each; options exclude{Data,Hooks,Views,Comments,...} normalized CE-side.

### Decisive source
```ts
// ordering invariant: models first, interfaces LAST (they reference models+columns+views)
let idMap = await this.importService.importModels(targetContext, { data: exportedModels, ... });
...
const exportedInterfaces = options.excludeInterfaces ? [] :
  await this.exportService.serializeInterfaces(context, { idMap: exportModelMap, req });  // serialized last
...
} catch (err) {
  if (targetBase?.id) {
    await this.projectsService.baseSoftDelete(targetContext, { baseId: targetBase.id, ... });
  }
  this.appHooksService.emit(AppEvents.BASE_DUPLICATE_FAIL, { ..., error: err.message });
  ...
  throw err;
}
// table-level failure: delete every model created so far
if (createdModels.length > 0) {
  for (const modelId of createdModels) {
    await this.tablesService.tableDelete(context, { tableId: modelId, forceDeleteRelations: true, req });
  }
}
```

**Flow:** serialize everything from the source (models → scripts → workflows → documents → dashboards → interfaces-last), then import in dependency order while threading one shared idMap; only then stream data per model (`streamModelDataAsCsv` → `importDataFromCsvStream` + separate link stream). Any throw lands in a catch that compensates: base-level ⇒ softDelete the target base; table-level ⇒ hard-delete created tables with relations.
**Invariant:** interfaces serialize LAST because their page configs reference models/columns/views — aliases must already be in the map. Compensation must run even when `targetBase` exists but data phase failed; success/failure app-hooks fire exactly once per path. Data streaming reuses the SAME two-stream pattern (data + links) with `handledLinks` carried across models to avoid double-inserting mm rows.
**Probe:** no unit test upstream. Source-grounded probe: `duplicate.processor.ts:226-233` — "serialized last" comment + call position; `:339-346` — softDelete-first catch; `:607-615` — createdModels rollback loop.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "duplicateBaseJob importModels idMap baseSoftDelete", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt serialize-in-dependency-order, single threaded idMap, and soft-delete/hard-delete compensation split; adapt entity types (scripts/workflows/dashboards are NocoDB-specific) and hook names to host; omit EE cross-workspace branch (throws NotImplementedException in CE). Coverage caveat: no in-repo tests; source-grounded.
