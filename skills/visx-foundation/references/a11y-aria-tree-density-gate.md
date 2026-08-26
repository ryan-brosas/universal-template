<!-- capsule-v2 -->
# ARIA tree generation + density gating — what roles/labels make an SVG readable to a screen reader, and when do you STOP emitting per-point labels?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** Which ARIA attributes go on svg/series/point, and why are point props dropped above a threshold instead of truncated?

## graphics-document → graphics-object → graphics-symbol ladder
**Path/Symbol:** `packages/visx-a11y/src/generators/ariaProps.ts:getChartAriaProps` (:42–79).
**Signature:** `getChartAriaProps<Datum>(config: ChartA11yConfig<Datum>): ChartA11yProps` (ids + svg + series[] + points[][]).
**Data Shape:** ids `{rootId, descriptionId: '<id>-description', tableId: '<id>-table'}`; `svg = {role:'graphics-document', 'aria-roledescription': chartTypeLabel, 'aria-label': title, 'aria-describedby': descriptionId}`.

### Decisive source
```ts
const includePointProps = normalized.pointCount <= pointDescriptionThreshold; // default 150
points: includePointProps
  ? normalized.series.map((series) =>
      series.data.map<ChartA11yPointProps>((_, index) => ({
        role: 'graphics-symbol',
        'aria-roledescription': config.locale?.pointRoleDescription ?? 'data point',
        'aria-label': getPointLabel(config, series, index),
      })))
  : normalized.series.map(() => []),   // EMPTY arrays — shape preserved

// pie/donut labels carry the computed share:
const share = total === 0 ? 0 : (config.y(datum, i, series.data) / total) * 100;
return `${x}, ${y} (${formatPercent(share)})`;
```

**Flow:** normalize data once (shared with keyboard nav) → emit root/series props always → emit per-point labels only under the threshold; the same threshold gates keyboard navigation in `useChartKeyboardNav` so a chart never announces 5,000 focusable points.
**Invariant:** dropping point props must preserve the ARRAY-OF-ARRAYS shape (`series.map(() => [])`) — consumers index `[seriesIndex][index]`; returning `undefined` would throw at spread sites. Pie labels must divide by the SERIES total and guard `total===0` → 0%.
**Probe:** `packages/visx-a11y/test/generators.test.ts :36/:44/:52-62` pins role strings incl. `'line chart'`, `'series'`, `'data point'`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "getChartAriaProps includePointProps", limit: 10, fields: ["signature", "name", "file"] });
// resolves packages/visx-a11y/src/generators/ariaProps.ts :42-79
```

## Verdict
Adopt the three-level role ladder + shape-preserving density gate verbatim; adapt threshold/locale defaults; omit the config type surface. Roles pinned by direct tests.
