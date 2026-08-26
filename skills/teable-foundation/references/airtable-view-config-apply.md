<!-- capsule-v2 -->
# Airtable view-config application — how does per-view, per-aspect isolation keep one failure from degrading the batch?

**Source:** teable AGPL `develop@06a4461e`; Codebase Memory `teable`. **Question:** How are created views paired back to their Airtable sources and how is each config aspect applied so failures stay granular?

## collectViewTargets + applyViewConfigs + applyMappedViewConfig
**Path/Symbol:** `apps/nestjs-backend/src/features/airtable-import/airtable-import.service.ts` — `collectViewTargets` (:565–583), `applyViewConfigs` (:590–643), `applyMappedViewConfig` (:645–707).
**Signature:** `private async applyMappedViewConfig(target: IViewConfigTarget, mapped, issues): Promise<void>` with inner `apply(label, run)` wrapper.
**Data Shape:** pairing relies on ORDER — "the v2 create-table mapper preserves view order, so the i-th created view matches the i-th planned source"; a type guard (`created.type === source.teableViewType`) skips drift; field-meta maps cache per table for filter resolution.

### Decisive source
```ts
const apply = async (label: string, run: () => Promise<unknown>) => {
  try { await run(); }
  catch (error) {
    this.logger.warn(`Failed to apply ${label} to view "${target.viewName}": ...`);
    issues.push({ code: 'viewConfigDegraded', tableName: target.tableName,
      viewName: target.viewName, reason: `could not apply ${label}` });
  }
};
if (mapped.filter) await apply('filters', () => ...setViewProperty(tableId, viewId, 'filter', ...));
if (mapped.sort)   await apply('sorting', () => ...);
if (mapped.group)  await apply('grouping', () => ...);
if (mapped.options) await apply('view options', () => ...patchViewOptions(...));
```

**Flow:** at table creation (importViewConfig on) each created view pairs with its planned source → after ALL fields exist, every target's config fetches from the share client → per-view try/catch isolates fetch/mapping failures as `viewConfigDegraded` issues → within a view, EACH aspect (filters / sorting / grouping / options) applies independently with its own catch-and-report → select-option names precomputed once across the base schema; per-table field meta fetched lazily once.
**Invariant:** View config is strictly last — sorts/groups referencing late-created lookups must resolve. One failed aspect never blocks the others; one failed view never blocks the batch. The whole importViewConfig plane is OPT-IN (default false) and everything under it degrades gracefully by construction.
**Probe:** Direct tests: `airtable-schema-mapper.spec.ts` it('maps supported views and reports skipped ones, defaulting to a grid') :352; service-level isolation behavior pinned via `airtable-view-config-mapper.spec.ts` drop-reporting tests (:90).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project":"teable","query":"applyViewConfigs collectViewTargets applyMappedViewConfig","limit":5,"detail":"ids"}'
```

## Verdict
Adopt ordered-pairing with type guards and label-scoped per-aspect error isolation for any post-hoc configuration applier; adapt property-setter API; omit Airtable share-fetch details (see airtable-share-client capsule). Coverage caveat: none.
