<!-- capsule-v2 -->
# Metadata three-pass load — how do you turn model configs into DB metadata without double-processing identifier names?

**Source:** strapi MIT Expat (non-EE) `develop@1fd9d80ad5f0a2c97d09ce7529f5cd9fdb91ca2d`; Codebase Memory `strapi`. **Question:** Given a list of model configs (uid, attributes, relations), how do you build the in-memory metadata Map (table names, column names, reverse maps) so that names are normalized exactly once and misconfiguration fails fast?

## Metadata load seam
**Path/Symbol:** `packages/core/database/src/metadata/index.ts:createMetadata` (lines 20–36); `packages/core/database/src/metadata/metadata.ts:Metadata.loadModels` (51–107), `Metadata.validate` (39–50), `createAttribute` (109–119), `columnToAttribute` derivation (93–101).
**Signature:** `createMetadata(models: Model[]): Metadata` where `Metadata extends Map<string, Meta>`; `Meta` adds `columnToAttribute`, `indexes`, `foreignKeys`, `lifecycles` to the raw model.
**Data Shape:** input models are deep-cloned; output Map is keyed by uid; each attribute gains a `columnName`; each meta gains a reverse `columnToAttribute` map (`columnName || key → key`).

### Decisive source
```ts
// loadModels — three passes over cloneDeep(models): init → build → derive
for (const model of cloneDeep(models ?? [])) {
  const tableName = identifiers.getTableName(model.tableName);
  this.add({ ...model, tableName, attributes: { ...model.attributes },
    lifecycles: model.lifecycles ?? {}, indexes: model.indexes ?? [],
    foreignKeys: model.foreignKeys ?? [], columnToAttribute: {} });
}
// build pass: every error is wrapped with attribute + model context
} catch (error) {
  if (error instanceof Error) {
    throw new Error(
      `Error on attribute ${attributeName} in model ${meta.singularName}(${meta.uid}): ${error.message}`
    );
  }
}
// derive pass: reverse map from column to attribute name
const columnToAttribute = Object.keys(meta.attributes).reduce((acc, key) => {
  const attribute = meta.attributes[key];
  if ('columnName' in attribute) {
    return Object.assign(acc, { [attribute.columnName || key]: key });
  }
  return Object.assign(acc, { [key]: key });
}, {});
```
```ts
// createAttribute — preset columnName is NEVER re-processed (prevents double shortening)
if ('columnName' in attribute && attribute.columnName) {
  return;
}
const columnName = identifiers.getColumnName(snakeCase(attributeName));
Object.assign(attribute, { columnName });
```
```ts
// validate — duplicate table names fail at load time, not at DDL time
if (seenTables.get(meta.tableName)) {
  throw new Error(
    `DB table "${meta.tableName}" already exists. Change the collectionName of the related content type.`
  );
}
```

**Flow:** `createMetadata` wraps `new Metadata().loadModels(models)` → pass 1 clones models and seeds Map entries with identifier-resolved `tableName` and empty bookkeeping fields → pass 2 walks every attribute: relational attributes dispatch to `createRelation` (which resolves targets against the Map and throws on missing/unknown/inversedBy mismatches), scalar attributes get a snake_case `columnName` unless one was preset → pass 3 derives the `columnToAttribute` reverse map for row→entity mapping → `validate()` scans all metas and throws on any duplicate `tableName`.
**Invariant:** caller configs are never mutated (`cloneDeep` before any assignment); an attribute that already carries a `columnName` is skipped by `createAttribute` so the identifier shortener can never run twice on the same name; every per-attribute failure is re-thrown wrapped with the attribute name AND model uid (the unwrapped path silently swallows non-Error throws); duplicate table detection runs after ALL models are loaded, so cross-model collisions are caught even when the colliding models are far apart in the list.
**Probe:** `packages/core/database/src/metadata/__tests__/metadata.test.ts` — parameterized attribute→columnName conversion table (`documentId`→`document_id`, preset `document_id` stays, camelCase→snake_case, json/datetime/arbitrary types), duplicate-table-name throw with the exact message, and relation error wrapping (`Metadata for "<target>" not found`, `Unknown relation`, inversedBy missing/non-relational).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "strapi", query: "loadModels createMetadata columnToAttribute", file_pattern: "packages/core/database/src/metadata/*", limit: 10, fields: ["signature", "name", "file"] });
```
Pass 3 note: Codebase Memory MCP was not connected in this session; the cited ranges were confirmed by direct read of the checkout at the pinned HEAD instead (see verification.md).

## Verdict
Adopt the three-pass shape (init → build-with-context-wrapped-errors → derive-reverse-map) plus the preset-skip rule for any config→schema compiler where names may already be canonical; adopt fail-fast duplicate-target validation at load time. Adapt the snake_case normalization and the identifier-shortener hook to your dialect's limits (see identifier-shortener capsule). Omit Strapi's relation-shape builders (`relations.ts` createRelation family) unless you port polymorphic relations too. Coverage: direct unit test exists and was read in full; no index-coverage caveat for these paths this pass (MCP disconnected — see verification.md).
