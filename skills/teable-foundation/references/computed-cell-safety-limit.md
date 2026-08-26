<!-- capsule-v2 -->
# Computed cell safety limit and chunked version-bump — enforcing per-cell byte ceilings without corrupting link projections or __version monotonicity

**Source:** teable AGPL `develop@06a4461e2bc53055182d4df0a72dffa26fd99210`; Codebase Memory `teable`. **Question:** When collected computed changes are size-checked before writeback, why are link fields exempt — and how does `__version` stay correct when field-chunking splits one logical update into many statements?

## Link-projection exemption + merged-chunk single version bump
**Path/Symbol:** `packages/v2/adapter-table-repository-postgres/src/record/computed/ComputedFieldUpdater.ts` — `ensureComputedChangesWithinLimit` (:1582–1623) with exemption comment :1598–1600; merge accumulator `mergeRecordChanges` (:100–121) keeping `oldVersion: Math.min(...)` :117; chunk decision `shouldChunkFields = collectChanges && !collapsedBatch && fieldIds.length > COMPUTED_UPDATE_FIELD_CHUNK_SIZE` (16, :79) at :1091–1092; per-chunk `incrementVersion: !shouldChunkFields` :1284; compensating bump :1344–1363 (`update … set "__version" = "__version" + 1 where "__id" in (changedRecordIds)`, source tag `'computed_version_bump'`).
**Signature:** `ensureComputedChangesWithinLimit(context, table, recordChanges): Promise<Result<void, DomainError>>`; error code `'validation.limit.computed_cell_value_max_bytes'`.
**Data Shape:** measures `measureJsonBytes(change.newValue)` against `limits.computed.maxComputedCellValueBytes` from the composed table-data-safety-limits config; changes keyed by recordId accumulate across field chunks.

### Decisive source
```ts
for (const change of recordChange.changes) {
  // Link values are a projection of junction/FK rows rather than an independent user value.
  // Rejecting a large projection leaves that cache stale even though the relation is valid.
  if (linkFieldIds.has(change.fieldId)) continue;
  const bytes = measureJsonBytes(change.newValue);
  if (bytes > limits.computed.maxComputedCellValueBytes)
    return err(domainError.validation({ code: 'validation.limit.computed_cell_value_max_bytes', ... }));
}
```
```ts
// Chunked collection path: each UPDATE..RETURNING runs WITHOUT its own version increment,
// changes are merged per-record (oldVersion = min across chunks), then ONE explicit bump:
if (shouldChunkFields) {
  recordChanges.push(...mergedRecordChanges.values());
  if (recordChanges.length > 0) {
    const versionBump = sql`update ${sql.raw(toQualifiedIdentifierLiteral(tableName))}
      set "__version" = "__version" + 1
      where "__id" in (${sql.join(changedRecordIds)})`.compile(db);
    await this.executeComputedQuery(db, versionBump, { source: 'computed_version_bump', ... });
  }
}
```
**Flow:** when collecting changes for event fan-out, wide steps split into ≤16-field chunks → every chunk executes with `incrementVersion:false` → returned rows merge into per-record change sets (min old-version so downstream consumers see the true pre-update version) → safety check runs on each chunk's rows (link-projected values exempt) → a single explicit `__version+1` statement covers exactly the records that changed.
**Invariant:** a rejected non-link computed value ABORTS the step (fail-closed) because an oversized formula/lookup result would poison caches; a rejected LINK projection would be wrong — the junction rows exist regardless of display size, so failing would leave the link cache stale-but-unfixable. And exactly-one version bump per changed record per run is what realtime sync relies on: per-chunk increments would double-count, zero increments would drop the change from sync.
**Probe:** `packages/v2/adapter-table-repository-postgres/src/record/computed/__tests__/ComputedFieldUpdater.spec.ts` — `"rejects oversized computed cell values returned from updates"` (:980), `"allows oversized junction-backed link projections to stay consistent"` (:1031), `"chunks wide same-level computed updates and bumps record versions once"` (:1093).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "teable", query: "ensureComputedChangesWithinLimit", limit: 5 });
// → ComputedFieldUpdater.ensureComputedChangesWithinLimit …/record/computed/ComputedFieldUpdater.ts 1582-1623
```

## Verdict
Adopt both asymmetries as-is: fail-closed on oversized computed values EXCEPT relation projections, and defer version increments out of chunks into one id-set bump. Adapt the byte ceiling source (`TableDataSafetyLimitComposer`) and `measureJsonBytes` to host equivalents. Omit span/log plumbing. Coverage caveat: none material — all three behaviors have direct spec tests at this pin.
