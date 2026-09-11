<!-- capsule-v2 -->
# Meta-update visitor — how does teable decide between an options-only field UPDATE and a full storage-metadata rewrite, and what must every statement carry?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** Which update specs may touch only `options`, which must rewrite derived columns, and what invariants apply to every UPDATE statement?

## options-only vs storage-metadata depth split with version-touch tracking
**Path/Symbol:** `packages/v2/adapter-repository-postgres/src/repositories/visitors/TableMetaUpdateVisitor.ts` — `buildFieldOptionsUpdate` (525–550), `buildFieldStorageMetadataUpdate` (552–586), dispatch map (588–844), `buildInsertOrReviveFieldStatement` (892–926), `mapRecordFilterToLegacy` (943–974), version-touch trackers (983–989); tests `TableMetaUpdateVisitor.spec.ts` (:178+, 'switches between option-only and storage-metadata link config updates' :564, 'persists derived user multiplicity metadata…' :586, 'uses storage metadata updates for rollup config changes' :605).
**Signature:** visits produce `ReadonlyArray<TableUpdateBuilder>` (Kysely UpdateQueryBuilder/InsertQueryBuilder/DeleteQueryBuilder union); `fieldVersionTouchOrder(): ReadonlyArray<string>`.

### Decisive source
```ts
// OPTIONS-ONLY: set { options, version: coalesce(version,0)+1, last_modified_time/by }
//   used by: showAs/formatting/defaultValue/notification/expression-only rollup… (~25 specs)
// STORAGE-METADATA: set { options, meta, cell_value_type, is_multiple_cell_value, db_field_type,
//   is_lookup, is_conditional_lookup, lookup_linked_field_id, lookup_options, version+1, … }
//   used by: user multiplicity (UpdateUserMultiplicity :673), formula EXPRESSION change (:761),
//   link config WHEN isRelationshipChanging()||isOneWayChanging() (:786-794), UpdateLinkRelationship (:796),
//   lookupOptions (:804 — comment: partial update would leave STALE metadata when lookupFieldId changes),
//   rollup config (:815 — derives lookup metadata from linkFieldId)
// insert-or-revive: insertInto('field').values(row).onConflict(id).doUpdateSet({ ...allColumns, deleted_time: null })
```

**Flow:** resolve the live domain field via predicate lookup → rebuild its persistence row through TableFieldPersistenceBuilder (so option serialization stays single-sourced) → choose depth by whether the spec can change DERIVED storage facts (multiplicity, cell value type, db type, linkage metadata), not just display options → track touched field ids in order → statements are accumulated by addCond and executed by the caller inside one transaction.
**Invariant:** DEPTH SELECTION IS THE CONTRACT: an options-only update of a relationship-changing link leaves stale `cell_value_type`/`lookup_options` and corrupts later reads. Every statement triple-pins scope: `id = ? AND table_id = ? AND deleted_time is null` — omitting table_id lets one table's update hit another's row after id reuse. Version increments use SQL-side `coalesce(version,0)+1`, never client counters. Insert-or-revive clears `deleted_time` on conflict so re-adding a removed field resurrects the same row.
**Probe:** `TableMetaUpdateVisitor.spec.ts` :564 asserts link-config routes to storage-metadata ONLY when relationship/oneWay changed; :605 pins rollup config → storage-metadata; :364 checks version-touch ordering.
**Coverage:** fully indexed.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "TableMetaUpdateVisitor buildFieldStorageMetadataUpdate buildFieldOptionsUpdate buildInsertOrReviveFieldStatement", limit: 10 });
```

## Verdict
Adopt the two-builder split and the per-spec routing table as-is — it encodes which columns are derived from options vs independent facts; adapt the builder union type to host ORM. The insert-or-revive upsert is the reusable primitive for soft-delete-plus-recreate domains.
