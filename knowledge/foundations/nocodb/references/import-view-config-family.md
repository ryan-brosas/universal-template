<!-- capsule-v2 -->
# View import family — how do grid/form/gallery views plus their filters, sorts, groups and hidden fields cross the Airtable→NocoDB boundary?

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f7513664f3f3`; Codebase Memory project `nocodb`. **Question:** What does each view type actually carry over, which parts are deliberately dropped, and what does the per-table name registry prevent?

## Type-specific creators over fetched view JSON, all funneling through nc_configureFields
**Path/Symbol:** `packages/nocodb/src/modules/jobs/jobs/at-import/at-import.processor.ts` — `nocoConfigureGridView` (:1913-2028), `nocoConfigureFormView` (:1827-1911), `nocoConfigureGalleryView` (:1773-1825), `nc_configureFields` (:2483-2576), `nc_configureFilters` (:2264-2381), `filterMap` (:2247-2262), `nc_configureSort` (:2463-2481), `nc_configureGroup` (:2386-2459), `viewNamesByTable` registry (:262-273).
**Signature:** each creator `(sDB, aTblSchema) → Promise<void>`; `getViewNames(tableId): string[]` lazily seeds a per-table array; call order in `job()`: grid → form → gallery (:2685-2687).
**Data Shape:** Airtable view payload `{columnOrder:[{columnId,visibility}], filters:{filterSet,conjunction}, lastSortsApplied:{sortSet}, groupLevels, metadata?.form}`; NocoDB writes go through viewColumnsService/formsService/gridsService/filtersService/sortsService/gridColumnService.

### Decisive source
```ts
// per-table unique view names (session-scoped registry):
const viewName = generateUniqueCopyName(aView?.name || 'Grid', viewNames,
  { prefix: null, separator: '_', counterFormat: '{counter}' });
viewNames.push(viewName);

// GRID: first grid reuses the table's default view; extra grids create
for (let i = 0; i < (sDB.options.syncViews ? gridViews.length : 1); i++) {
  ...
  let ncViewId = viewList?.list?.find((x) => x.tn === viewName)?.id;
  if (i > 0) { /* gridViewCreate + sMap.addToMappingTbl(gridViews[i].id, ...) */ }
  await nc_configureFields(ncViewId, vData, ..., 'grid');
  // skip filters if nested
  if (!vData.filters.filterSet.find((x) => x?.type === 'nested'))
    await nc_configureFilters(ncViewId, vData.filters);
  if (vData?.lastSortsApplied?.sortSet.length) await nc_configureSort(...);
  if (vData?.groupLevels) await nc_configureGroup(...);
}

// FORM: remote returns NO form object when everything is default ⇒ seed defaults
let refreshMode = 'NO_REFRESH';
if (vData.metadata?.form) {
  if (vData.metadata.form?.refreshAfterSubmit) refreshMode = ...;
}
const formData = {
  title: viewName, heading: viewName, description: viewDescription,
  subheading: desc, success_msg: msg,
  submit_another_form: refreshMode.includes('REFRESH_BUTTON'),
  show_blank_form:      refreshMode.includes('AUTO_REFRESH'),
};

// GALLERY: fetches view data but DISCARDS it — only title/description port
await getViewData(galleryViews[i].id);        // return value never bound

// FIELDS: sys columns forced hidden BEHIND every imported column
const configData = { show: c[j].visibility, order: j + 1 };
...
await this.viewColumnsService.columnUpdate(context, {
  viewId, columnId: ncViewColumnId, internal: true,
  column: { show: false, order: j + 1 + c.length }, req });   // ncRecordId/Hash

// FILTER translation incl. select-option id remap via sMap:
else if (datatype === UITypes.SingleSelect || datatype === UITypes.MultiSelect) {
  if (filter.operator === 'doesNotContain') filter.operator = 'isNoneOf';
  if (Array.isArray(filter.value))
    for (let j = 0; j < filter.value.length; j++)
      filter.value[j] = await sMap.getNcNameFromAtId(filter.value[j]);  // id→title!
```

**Flow:** grid phase walks every table; with `syncViews:false` it still processes exactly ONE grid view (the default) — turning views off means "no EXTRA views", not zero configuration. The first grid binds to the auto-created default view (found by `tn === viewName`), later ones create new grids and register `gridViews[i].id → viewCreated.id` in `sMap` so later phases can reference them. Every creator fetches remote view data via `getViewData` (counted in `rtc.fetchAt`), then: grid ports fields/filters/sorts/groups; form ports fields plus per-field label/required/description from `metadata.form.fieldsByColumnId`; gallery ports NOTHING but title/description — its fetched payload is intentionally unbound. All three end in `nc_configureFields`, which first force-hides the two system columns (`ncRecordId`/`ncRecordHash`) at orders AFTER the imported set (`j+1+c.length`), then replays Airtable's `columnOrder` as `{show, order}` updates, overlaying form metadata when `viewType==='form'`.
**Invariant:** (1) Select-option FILTER values are AIRTABLE CHOICE IDS that must be translated through `sMap.getNcTypeOptions`' registrations — schema-time `getNocTypeOptions` calls `sMap.addToMappingTbl(choice.id, undefined, choice.name)` (:542-546) precisely so filter time can resolve them; break that pairing and every select filter silently maps to nothing (skip-logged). (2) Nested filter trees are skipped wholesale (`type === 'nested'` check) — flat-only support is deliberate. (3) Operator map includes `'|'→anyof` and `'&'→allof`; `doesNotContain` rewrites to `isNoneOf` ONLY for select datatypes; link-column filters are always skip-logged (NocoDB can't express textual link filters). Date ops split `isWithin` (sub-op = mode, value = numberOfDays) from exact-date comparisons. (4) Grouping has a datatype allowlist (Date/DateTime/LTAR/selects/text/formula/checkbox/collaborator/number); everything else skip-logged; direction string 'ascending'→'asc'. (5) `rtc.sort++` counts ATTEMPTED sorts even when the column never migrated — stats are effort counters, not success counters. (6) Per-table view-name dedupe lives in a job-local `Map` seeded ONLY by this run's creations plus (in sync-into-existing mode) existing tables' titles — two concurrent imports into different bases use different processor instances, so no cross-talk.
**Probe:** no unit test upstream. Deterministic probes: `at-import.processor.ts:1927` — the `syncViews ? gridViews.length : 1` bound; `:1869-1876` — absent-metadata default ladder; `:1789` — gallery fetch with discarded result; `:2515-2537` — sys-column hide with `order: j + 1 + c.length`; `:2309` — filter-value id remap through sMap; `:2010` — nested-filter skip.
**Coverage caveat:** file indexed clean; claims from whole-file read at f7513664; no direct tests cover these closures.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "nocoConfigureGridView nc_configureFields filterMap generateUniqueCopyName groupLevels fieldsByColumnId", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shape "one creator per view type over fetched JSON, shared field-order replier, explicit skip-log for unsupported operators/datatypes" for any source→target view migration. Adapt the form-refresh enum mapping and filter operator table to your target's grammar. OMIT gallery content porting only if your target has no equivalent field-hiding concept — here it's a documented no-op, not an oversight.
