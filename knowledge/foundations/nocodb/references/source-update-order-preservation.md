<!-- capsule-v2 -->
|# Source.update order preservation — legacy missing-order backfill and the default-source floor

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** What must a generic row-update method do when updates hit rows whose ordering metadata predates the column — the small invariant every CRUD port forgets?

## Path/Symbol
`packages/nocodb/src/models/Source.ts:Source.update` (order-repair block within 224–260).

**Signature:** `static async update(context, sourceId, source, ncMeta = Noco.ncMeta)`.

**Data Shape:** extractProps ALLOWLIST (alias/config/type/is_meta/is_local/order/enabled/meta/deleted/fk_sql_executor_id/is_schema_readonly/is_data_readonly/fk_integration_id/is_encrypted) gates writability; config passes encryptConfigIfRequired before persist; meta stringified when present in payload.

### Decisive source
```ts
// if order is missing (possible in old versions), get next order
if (!oldSource.order && !updateObj.order) {
  updateObj.order = await ncMeta.metaGetNextOrder(MetaTable.SOURCES, { base_id: oldSource.base_id });
  if (updateObj.order <= 1 && !oldSource.isMeta()) {
    updateObj.order = 2;          // keep order 1 for default source
  }
}
// ... after write:
await NcConnectionMgrv2.bumpSourceVersion(oldSource);   // bump only, no local reset
```

**Flow:** fetch old row (404 when absent) → allowlist-project → encrypt config → fill type from old when absent → repair legacy missing order → persist → updateRelatedCaches fire-and-forget → bump version for cross-server invalidation → return fresh get().

**Invariant:** (1) Order repair keys off BOTH sides missing (`!old.order && !updateObj.order`) — never overwrite an explicit reorder with a computed one. (2) Order 1 is RESERVED for the default (meta) source: external sources floor at 2. (3) Allowlisted projection means new columns don't become writable by accident. (4) Bump-not-reset pairs with connection-reset-protocol.md's caller contract.

**Probe:** no unit test upstream. Source-grounded probe: Source.ts order-repair + floor lines verbatim above; :229-234 bump-only comment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "metaGetNextOrder extractProps encryptConfigIfRequired", limit: 8, fields: ["signature","name","file"] });
```

## Verdict
Adopt both-sides-missing order repair with a reserved slot floor and allowlisted projection; adapt field lists; omit nothing. Coverage caveat: no in-repo unit tests; source-grounded.
