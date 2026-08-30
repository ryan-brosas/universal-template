<!-- capsule-v2 -->
# Field dependency graph — how do you know which computed fields must recompute when a cell changes, across linked tables?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How is a cross-table field-level dependency graph loaded from SQL metadata and traversed to find ALL transitive dependents of changed fields?

## Pure edge-builder + SQL-loaded graph loader
**Path/Symbol:** pure builder `packages/v2/field-dependency-core/src/edge-builder.ts`: `buildLookupEdges` (16–44), `buildRollupEdges` (51–79), `buildLinkEdges` (85–101), `buildConditionalEdges` (111–153), `buildDerivedEdgesFromField` (155–182), `mergeEdges` (196+); parsers `parsers.ts` (`parseLookupOptions` :166, `parseConditionalFieldOptions` :199, `extractConditionFieldIds` :77); loader `packages/v2/adapter-table-repository-postgres/src/record/computed/FieldDependencyGraph.ts:FieldDependencyGraph.load` (196–220) with `loadFull` (285+) / `loadIncremental` (848+) and closure expansion `findAffectedFieldIds` (1075–1410).
**Signature:** edges are data: `{fromFieldId, toFieldId, fromTableId, toTableId, kind: 'same_record'|'cross_record', semantic: 'lookup_link'|'lookup_source'|'rollup_source'|'link_title'|'conditional_*_source', linkFieldId?}`; `load(baseId?, opts): Promise<Result<FieldDependencyGraphData, DomainError>>`.
**Data Shape:** `FieldMeta` = parsed field options (link: foreignTableId+lookupFieldId; lookup: linkFieldId+foreignTableId+lookupFieldId; conditional adds filterDto condition field ids); graph data carries fields + edges + filter-field metadata hydration.

### Decisive source
```ts
// buildLookupEdges — ONE lookup field produces TWO edges of different kinds:
return [
  { fromFieldId: options.linkFieldId,   toFieldId: fieldId,
    fromTableId: tableId,               toTableId: tableId,
    kind: 'same_record', semantic: 'lookup_link' },        // recompute when MY row's link changes
  { fromFieldId: options.lookupFieldId, toFieldId: fieldId,
    fromTableId: options.foreignTableId, toTableId: tableId,
    kind: 'cross_record', linkFieldId: options.linkFieldId,
    semantic: 'lookup_source' }];                          // recompute when ANY linked row's source changes
// buildLinkEdges — a link depends on the FOREIGN title field, propagating THROUGH itself:
{ fromFieldId: options.lookupFieldId, toFieldId: fieldId,
  fromTableId: options.foreignTableId, toTableId: tableId,
  kind: 'cross_record', linkFieldId: fieldId /* the link field itself */, semantic: 'link_title' }
```

**Flow:** field options JSON from metadata tables → tolerant parsers (`readString/readOptionalBoolean`, filter DTOs) → per-type edge builders emit the edge pairs above → `mergeEdges` dedupes → traversal from changed seed fields follows BOTH same-record edges (row-scoped recompute) AND cross-record edges through `linkFieldId` (the join column) into foreign tables, expanding transitively until fixpoint; incremental loads restrict to known-dirty field ids, full loads rebuild base-wide. Provision-state filtering keeps tables that are `pending`/`deleting` out of results.
**Invariant:** the direction convention is UNIFORM — `from` = dependency (upstream, changes), `to` = dependent (downstream, recomputes); cross-record edges MUST carry their `linkFieldId` or propagation cannot hop tables (this is why link_title sets `linkFieldId` to the link field ITSELF); a lookup is never just "one dependency" — dropping either of its two edges silently misses updates.
**Probe:** `packages/v2/field-dependency-core/src/edge-builder.spec.ts::"creates two edges for lookup field"` (:22), `::"creates link_title edge for link field"` (:82), `::"skips duplicate condition field if same as lookup field"` (:152); pglite loader tests `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/FieldDependencyGraph.pglite.spec.ts::"finds lookup dependents from seed link fields via lookup_linked_field_id with JSON fallback"` (:534), `::"continues through a reference-to-legacy-to-reference dependency chain"` (:658).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable",
  query: "buildLookupEdges buildDerivedEdgesFromField mergeEdges", limit: 10,
  fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the typed-edge dependency model (same_record vs cross_record + semantics) and the pure builder/parser split — testable without a DB, portable to any metadata store. Adopt the two-edges-per-lookup rule and link-as-propagation-channel convention. Adapt option schemas, storage layout (teable reads v1 JSON columns), and cycle policy to host. Caveat: `FieldDependencyGraph.ts` parse_partial at 1131/1202/1339 (outside cited ranges); loader probes run against pglite fixtures upstream.
