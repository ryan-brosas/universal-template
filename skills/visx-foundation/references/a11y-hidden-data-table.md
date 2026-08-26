<!-- capsule-v2 -->
# Hidden data-table twin — how do you expose a chart's full data to screen readers without changing layout?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** What is the correct visually-hidden table construction (CSS, header logic, ragged-series cells) and why must every cell be HTML-escaped?

## Visually-hidden class + ragged-column table builder
**Path/Symbol:** `packages/visx-a11y/src/utils/table.ts:getChartA11yTable` (:55–81) + `VISUALLY_HIDDEN_STYLE(_STRING)` (:6–19); renderer `generators/dataTableHTML.ts:generateDataTableHTML` (:7–24); announcer component `components/ChartA11yAnnouncer.tsx` (:18–42).
**Signature:** `getChartA11yTable(config): {id, caption, headers: string[], rows: string[][]}`; `generateDataTableHTML(config): string`.
**Data Shape:** rows are padded to `maxSeriesLength`; missing cells become `''` (never skipped) so columns stay aligned; multi-series headers `[xLabel, ...seriesLabels]`, single-series collapses to `[xLabel, yOrSerieslabel]`.

### Decisive source
```ts
export const VISUALLY_HIDDEN_STYLE_STRING =
  'position:absolute;width:1px;height:1px;padding:0;margin:-1px;' +
  'overflow:hidden;clip:rect(0, 0, 0, 0);white-space:nowrap;border:0;';
```
```html
<!-- dataTableHTML — scope + escape on EVERY cell, caption inside table -->
<table id="..." style="...hidden...">
  <caption>...</caption>
  <thead><tr><th scope="col">Jan &amp; Feb</th>...</tr></thead>
  <tbody><tr><th scope="row">...</th><td>$10</td></tr></tbody>
</table>
```

**Flow:** normalize → build headers (histogram xLabel defaults to `'Bin'`, else `'Category'`) → iterate index 0..maxSeriesLength, x-cell from FIRST series having a datum at that index (`getFirstDatumAtIndex`), y-cells per series or `''`. Announcer twin: `role={politeness==='assertive'?'alert':'status'}` + `aria-live` + `aria-atomic`, same hidden style when not visible.
**Invariant:** (1) the clip-rect hidden style keeps the table in the accessibility tree while removing it from layout — `display:none` would hide it from screen readers too; (2) string interpolation into HTML REQUIRES `escapeHtml` on every cell/header/caption/id (test pins `&amp;` output); (3) empty-string padding is what preserves column alignment for ragged series.
**Probe:** `packages/visx-a11y/test/dataTable.test.tsx :92 expect(html).toContain('Jan &amp; Feb')`; `test/generators.test.ts :144`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "getChartA11yTable VISUALLY_HIDDEN_STYLE", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-a11y/src/utils/table.ts :55-81
```

## Verdict
Adopt hidden-style constant, scoped-header table shape, escape discipline, and announcer role mapping verbatim; adapt labels/caption locale; omit React component wrappers if your host renders differently.
