<!-- capsule-v2 -->
# Config-observation twins — how do saved views and relation fields become query analytics WITHOUT a request ever running?

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** How do you feed configuration-defined queries (views, lookup/link conditions) into the same observation pipeline as executed queries?

## Synthetic one-request windows with config-sourced diagnostics
**Path/Symbol:** `packages/v2/table-query-ops/src/savedViewConfigObservation.ts` whole (55L): `buildSavedViewConfigObservation`; `relationFieldConfigObservation.ts` (240L): `buildRelationFieldConfigObservation` (:36-102), per-kind extractors (:104-183: conditionalLookup→options, conditionalRollup→config, lookup→lookupOptions, link→config), `readTargetViewConfig` (:185-198), `mergeFilters` (:200-209), duck-typed `callNoArg` (:233-237).
**Signature:** both return `Result<TableQueryObservationWindow | undefined, DomainError>` — undefined = "nothing interesting", NOT an error.
**Data Shape:** synthetic windows carry `requestCount:1, slowCount:0, totalDurationMs:0` and ONE diagnostic whose `statementKind` is `VIEW_CONFIG`/`RELATION_FIELD_CONFIG` and whose fingerprint embeds provenance: `saved_view_config:<viewId>:<shapeHash>` / `relation_field_config:<kind>:<sourceTable>:<sourceField>:<shapeHash>`.

### Decisive source
```ts
const viewConfig = readTargetViewConfig(input.targetTable, relation.filterByViewId);
const filter = mergeFilters(relation.condition?.filter, viewConfig.filter);   // AND-wrapped
const sort  = relation.condition?.sort ?? viewConfig.sort;                    // condition wins
…
if (!hasTargetFilter && !hasTargetSort) return ok(undefined);   // no-op is SUCCESS here
return TableQueryObservationWindow.create({ …, shape: shape.value,
  sqlDiagnostics: [{ source: 'relation_field_config', statementKind: 'RELATION_FIELD_CONFIG',
    fingerprint: `relation_field_config:${kind}:${sourceTable}:${fieldId}:${shape.shapeHash()}`,
    parameterCount: 0, sampled: false }] });
```

**Flow:** field-type dispatch → duck-typed option accessors (`callNoArg` guards method presence — fields come from multiple mapper generations) → target view defaults read via `getViewById().queryDefaults()` → filters merged (condition AND view-default) → shared `buildQueryConfigShape` produces the SAME literal-free shape as live traffic → window enters the normal sink so hot views/relation targets rank in the advisor exactly like slow real queries.
**Invariant:** Zero-duration windows are first-class — the risk policy's `minRequestsPerWindow` and count gates treat them like any observation; only their latency signals are zero. Provenance lives in the diagnostic fingerprint (queryable), never in the hashed shape (which must stay structure-only). Extractors return undefined for missing methods rather than throwing — version skew tolerance.
**Probe:** `savedViewConfigObservation.spec.ts:76/:113/:146` (literal-free shapes, formula source evidence, IF pushdown); `relationFieldConfigObservation.spec.ts:73/:166`.
**Coverage caveat:** none for extraction semantics; merge precedence (condition-over-view-sort) pinned by test fixtures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "buildRelationFieldConfigObservation buildSavedViewConfigObservation callNoArg", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt config-as-observation with zero-duration windows + provenance fingerprints; adapt extractor dispatch to your field model; keep undefined-means-nothing-interesting semantics — conflating it with error poisons callers.
