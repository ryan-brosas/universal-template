<!-- capsule-v2 -->
# Per-view-type extras remap — how does export carry kanban grouping, calendar ranges, timeline ranges, and gantt dependencies without orphaning field ids?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** View-type-specific payloads (kanban meta stacks, calendar/timeline ranges, gantt date dependencies) hide column references outside the generic fk_* switch — how does export translate them?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.serializeModels` — `view.view` extras switch at lines 489–615.

**Signature:** inline in the per-view loop: `for (const [k, v] of Object.entries(view.view)) { switch (k) { … } }` — operates on the eager-loaded `view.view` object populated by each View subclass's `.get()`.

**Data Shape:** `view.view` holds type-specific rows: KANBAN `meta` (stack map keyed by column id → array of `{fk_column_id,id,…}` ops), CALENDAR `calendar_range[]` (`fk_from_column_id`,`fk_to_column_id?`), TIMELINE `timeline_range[]` (same shape), GANTT `date_dependency` (`fk_start_date_field_id`,`fk_end_date_field_id`,`fk_duration_field_id`,`fk_dependency_linkrow_field_id` + behavior knobs).

### Decisive source
```ts
case 'levels':   // LIST view hierarchy levels — map model/link refs, null-safe
  view.view[k] = v.map(level => ({
    level: level.level,
    fk_model_id: idMap.get(level.fk_model_id) ?? level.fk_model_id,
    fk_link_column_id: level.fk_link_column_id ? idMap.get(...) ?? ... : null, … }));
case 'meta':     // KANBAN: re-key stack map from old colId → mapped colId
  const meta = parseMetaProp(view.view);
  for (const [k, v] of Object.entries(meta)) {
    if (!Array.isArray(v)) continue;            // non-array meta untouched
    const colId = idMap.get(k);
    for (const op of v) { op.fk_column_id = idMap.get(op.fk_column_id); delete op.id; }
    meta[colId] = v; delete meta[k]; }
  view.view.meta = meta;
case 'calendar_range': case 'timeline_range':
  view.view[k] = range.map(r => ({ fk_from_column_id: idMap.get(r.fk_from_column_id),
                                   fk_to_column_id: r.fk_to_column_id ? idMap.get(r.fk_to_column_id) : null }));
case 'date_dependency':  // GANTT: rebuild object, mapping all four field refs
  view.view[k] = { is_active: dep.is_active, fk_start_date_field_id: dep.… ? idMap.get(dep.…) : null, … };
case 'created_at': case 'updated_at': case 'fk_view_id': case 'base_id':
case 'source_id': case 'uuid':
  delete view.view[k];
```

**Flow:** the view loop first registers `${idMap.get(model.id)}::${view.id}` into idMap, loads view columns/filters/sorts, rewrites filters to composite ids (`${idMap.get(view.id)}::${fl.id}`, group parents prefixed, groups dropping value/comparison keys) and sorts to `{fk_column_id→mapped, direction, enabled}` triples, THEN walks `view.view` with this type-gated switch. Generic `view.view` column refs (`fk_column_id`, cover/grp/prefix image cols) map directly.

**Invariant:** each extra is gated on `view.type === ViewTypes.<X>` because the eager-loaded key only exists for that subtype — running the rewrite unguarded would corrupt unrelated view types sharing a key name. Kanban meta is DOUBLE-keyed (the stack map's KEYS are column ids too), so both keys and values must be remapped, non-array meta passed through untouched, and per-op row identity (`op.id`) deleted. Optional range endpoints (`fk_to_column_id`) may be absent — map-or-null, never crash. Timeline ranges mirror calendar exactly (the comment says so deliberately) so the importer can share one reconstruction path.

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:498-517` (levels null-safety), `:518-535` (kanban double-keying), `:536-571` (range twins incl. timeline comment), `:572-603` (gantt dependency rebuild); import-side counterpart resolves these ids back through idMap during `importModels`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "serializeModels calendar_range timeline_range date_dependency parseMetaProp", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the type-gated extras switch with map-or-null optional endpoints and double-keyed meta remapping; adapt the view-type enum and extra names to host; omit LIST levels/gantt knobs unless your views carry them. Coverage caveat: no in-repo unit tests; source-grounded.
