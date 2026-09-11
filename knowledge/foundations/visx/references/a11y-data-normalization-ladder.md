<!-- capsule-v2 -->
# Data normalization ladder — one function that accepts flat, nested, or per-series data and labels every series

**Source:** visx (ui-visx) MIT `master@485c0359664ee8e612992defb16e1f035ed40b23`; Codebase Memory `ext-ui-visx`. **Question:** What is the canonical input shape for all a11y generators/nav, and how are ambiguous flat-vs-nested inputs resolved?

## series config > nested arrays > wrap-flat
**Path/Symbol:** `packages/visx-a11y/src/utils/data.ts:normalizeChartA11yData` (:49–80); discriminator `isNestedSeriesData` (:20–31); label fallback `getSeriesLabel` (:33–47).
**Signature:** `normalizeChartA11yData<Datum>({data, series}): {series: {index,label,data}[], isMultiSeries, pointCount, maxSeriesLength}`.
**Data Shape:** output series ALWAYS carry `{index, label: string, data: readonly Datum[]}` — every downstream consumer (aria, description, table, keyboard lengths) reads only this shape.

### Decisive source
```ts
function isNestedSeriesData(data, seriesConfig) {
  const firstDatum = data[0];
  if (!Array.isArray(firstDatum)) return false;
  return (seriesConfig?.length ?? 0) > 1;   // nested ONLY if >1 series configured!
}

if (seriesConfig?.some((series) => series.data)) {
  seriesData = seriesConfig.map((series) => series.data ?? []);   // 1) explicit wins
} else if (isNestedSeriesData(data, seriesConfig)) {
  seriesData = data;                                              // 2) nested arrays
} else {
  seriesData = [data];                                            // 3) flat wrapped
}
```

**Flow:** precedence ladder → label per series (`fn(index)` > static string > `'Data'` when single-series else `` `Series ${i+1}` ``) → aggregate `pointCount`/`maxSeriesLength` in the same pass.
**Invariant:** a chart with TWO datum-arrays but ZERO/one series configs stays FLAT-wrapped (the second array would be treated as datums) — the `>1` guard exists because single-nested-array input is ambiguous with "flat array of tuple-datums". Porters who drop that guard break every flat-input caller. `?? []` keeps misconfigured series as empty rather than crashing reducers.
**Probe:** `packages/visx-a11y/test/data.test.ts` (ladder + label fallbacks); consumed by keyboard flows in `test/keyboard.test.tsx :147+`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ui-visx", query: "normalizeChartA11yData isNestedSeriesData", limit: 10, fields: ["signature", "name", "file"] });
```
(CLI twin: `search_graph '{"project":"ext-ui-visx","query":"normalizeChartA11yData","limit":5,"detail":"ids"}'` → utils/data.ts :49-80.)

## Verdict
Adopt ladder + guard + label defaults verbatim; adapt the `ChartA11ySeriesConfig` type to host; omit nothing else — this file is self-contained.
