<!-- capsule-v2 -->
# Description generator dispatch — how do you turn chart data into one useful sentence for dense vs small vs pie charts?

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** A 10k-point line chart can't be read point-by-point — what summary strategy does visx use per chart type and size?

## Four-way dispatch on type + pointCount
**Path/Symbol:** `packages/visx-a11y/src/generators/description.ts:generateChartDescription` (:100–125); `generateDenseDescription` (:30–52), `generatePieDescription` (:54–79), `generateSmallSeriesDescription` (:81–98).
**Signature:** `generateChartDescription<Datum>(config): string`.
**Data Shape:** input normalized via shared `normalizeChartA11yData`; numeric collection filters non-finite y (`Number.isFinite`) BEFORE stats; pie sorts a COPY (`[...segments]`) to find smallest/largest.

### Decisive source
```ts
if (config.description) return config.description;          // explicit override wins
if (normalized.pointCount === 0) return `${label} "${title}" has no data.`;
if (config.chartType === 'pie' || config.chartType === 'donut') return generatePieDescription(config);
if (normalized.pointCount > threshold ||
    config.chartType === 'scatter' || config.chartType === 'heatmap') {
  return generateDenseDescription(config);
}
return generateSmallSeriesDescription(config);
```

**Flow:** dense → "N data points. Values range from MIN to MAX with an average of MEAN" (min/max/mean in ONE reduce pass); small → narrative with first/last/min/max anchors ("start at …, end at …, range from … at X"); pie → total + largest/smallest segments with percent share.
**Invariant:** scatter/heatmap are ALWAYS dense regardless of count (point-wise narration is meaningless there); explicit `config.description` short-circuits everything; the mean is rounded via `Math.round(mean * 100) / 100` only in the String fallback (formatted path uses `config.formatY`).
**Probe:** `packages/visx-a11y/test/generators.test.ts` pins generated strings; HTML escape twin: `:144 expect(html).toContain('<th scope="row">Jan &amp; Feb</th><td>$10</td>')`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "generateChartDescription generateDenseDescription", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dispatch ladder + single-pass stats + non-finite filtering; adapt sentence templates to your locale; omit visx config typing. Strings pinned by direct tests.
