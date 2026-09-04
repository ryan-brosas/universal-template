<!-- capsule-v2 -->
# ICS calendar export — paged VEVENT streaming with privacy-narrowed descriptions and RFC-5545 UID guarantees

**Source:** nocodb (Sustainable Use License, develop branch) `develop@f751366`; Codebase Memory project `nocodb`. **Question:** How does a calendar view stream rows as iCalendar events — which columns become which ICS properties, how are anonymous exports scoped, and what makes UIDs stable?

## Path/Symbol
`packages/nocodb/src/modules/jobs/jobs/export-import/export.service.ts:ExportService.streamModelDataAsIcs` (1445–1672) + `~/helpers/icsHelpers:{buildVEvent, icsCalendarHeader, ICS_CALENDAR_FOOTER, ICS_NEWLINE}`.

**Signature:** `streamModelDataAsIcs(context, {dataStream, baseId, modelId, viewId?, ncSiteUrl?, filterArrJson?, sortArrJson?, locale?, restrictToViewVisibleColumns?}): Promise<void>`.

**Data Shape:** header → `VEVENT…\r\n` chunks (one per row with a start value) → `ICS_CALENDAR_FOOTER` → null. Event fields: UID `${recordId}@${view.id}.nocodb`, DTSTAMP = one `new Date().toISOString()` for the whole export, SUMMARY = display column, DESCRIPTION = `"${col.title}: ${serialized}"` lines, start/end from range columns, URL = deep link `{site}/{workspace}/{base}/{table}/{view}?rowId=`.

### Decisive source
```ts
// Anonymous-path scoping: description can only contain columns the SHARED view shows
let visibleColumnIds: Set<string> | null = null;
if (param.restrictToViewVisibleColumns) {
  const viewColumns = await View.getColumns(context, view.id);
  visibleColumnIds = new Set(viewColumns.filter(vc => vc.show).map(vc => vc.fk_column_id));
}
// Authenticated path: calendar views usually hide every non-date field, so read the MODEL's
const descriptionColumns = model.columns.filter(c => !isSystemColumn(c) && !isLinksOrLTAR(c)
  && !isVirtualCol(c) && c.id !== fromColumn.id && (!toColumn || c.id !== toColumn.id)
  && (!displayColumn || c.id !== displayColumn.id) && (!visibleColumnIds || visibleColumnIds.has(c.id)));
// RFC 5545: UID must be globally unique; guard empty pk (&&/?? would let '' through)
const hasRealPk = pkValue !== null && pkValue !== undefined && pkValue !== '';
const recordId = hasRealPk ? pkValue : `${offset}-${i}`;
const recordUrl = param.ncSiteUrl && hasRealPk ? `${param.ncSiteUrl}/...?rowId=${encodeURIComponent(String(pkValue))}` : undefined;
```

**Flow:** hard-gates on `view.type === CALENDAR` + a configured `CalendarRange` (first range's from-column required). Reads via `datasService.dataList` in 200-row pages with `getHiddenColumns: true` (view filters still honored) — skipping rows without a start date, serializing summary/description through `serializeCellValue`, pushing each `buildVEvent` result + newline. Terminates footer+null on isLastPage or empty page; error path pushes null THEN rethrows so the consumer's stream ends.

**Invariant:** the description column set is an INTERSECTION with `visibleColumnIds` only on the public path — flipping that flag on authenticated exports would leak hidden-column values into a shareable feed. Range fields and the display column are EXCLUDED from the description (each maps to a dedicated ICS property already). UID fallback (`offset-index`) is unique per export but NOT stable across re-exports — only real PKs give stable UIDs, and the deep-link URL is emitted only when a real pk exists (a synthetic id wouldn't resolve).

**Probe:** no unit test upstream. Source-grounded probe: `export.service.ts:1469-1483` (calendar/range gates), `:1514-1541` (visible-columns intersection + description filter), `:1579-1585` (`getHiddenColumns: true` comment), `:1591-1598` (skip no-start rows), `:1622-1640` (UID guard + conditional URL), `:1667-1670` (error pushes null then throws).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "nocodb", query: "streamModelDataAsIcs buildVEvent icsCalendarHeader CalendarRange", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt property-per-column event assembly with the anonymous visible-columns intersection and the empty-pk UID guard; adapt ICS helpers/timezones to host; omit the deep-link URL unless your host has matching routes. Coverage caveat: no in-repo unit tests; source-grounded.
