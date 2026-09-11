<!-- capsule-v2 -->
# Stratified scatter sampling — how does a 30-cell ASCII chart stay honest over 10,000 runs?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** Which runs get plotted when results exceed the point budget, and how are bucket representatives chosen?

## renderScatterPlot — first + median-of-bucket ×19 + last ×10, run-number reconstruction
**Path/Symbol:** `extensions/pi-autoresearch/src/dashboard/scatter-plot.ts:23–65` (sampling), :113–162 (cell fill + symbol precedence), :174–207 (axis label alignment).
**Signature:** `renderScatterPlot(results, metricUnit, width, th, currentRunIndex?)`; budget `maxPoints=30`, `reservedForRecent=10` ⇒ 19 bucketable middle slots.
**Data Shape:** grid `chartHeight=10` rows × `chartWidth=min(60, width−12)`; symbols ● keep / ○ discard / 💥 crash / ⚠ checks_failed / ◐ current-running.

### Decisive source
```ts
const bucketSize = Math.max(1, Math.ceil(middle.length / bucketableCount));
for (let i = 0; i < middle.length; i += bucketSize) {
  const bucket = middle.slice(i, i + bucketSize);
  // Use median metric for representative point (more stable than min/max)
  const sortedByMetric = [...bucket].sort((a, b) => a.metric - b.metric);
  const medianResult = sortedByMetric[Math.floor(sortedByMetric.length / 2)];
  bucketed.push(medianResult);
}
// x labels reconstruct ORIGINAL run numbers: 1, bucket centers (capped before recent window), last 10
```

**Flow:** ≤30 results plot verbatim. More: keep FIRST row (baseline), split the middle into ≤19 equal buckets each represented by its METRIC-median member, always keep the last 10 verbatim (recent detail where the eye looks). X-axis prints three reconstructed original run numbers (first/mid/last) so the compressed chart stays addressable. Cell collisions resolve by precedence — a meaningful symbol replaces an existing '·', never the reverse.
**Invariant:** median-of-bucket (not min/max) prevents outlier runs from painting trends that never happened — the in-source comment marks this as deliberate. The baseline is ALWAYS visible so every chart shows its reference point. Bucket-center run numbers are capped at `results.length − reservedForRecent` so labels never claim positions inside the recent window twice.
**Probe:** anchors: `grep -nE 'medianResult|sortedByMetric' extensions/pi-autoresearch/src/dashboard/scatter-plot.ts | cut -d: -f1` → :47, :48, :49 (bucket sort + median pick); `grep -n reservedForRecent extensions/pi-autoresearch/src/dashboard/scatter-plot.ts | cut -d: -f1` → :25 (const), :35, :37–38 (runNumbers build), :60, :63 (label caps) — 6 lines; fullscreen-only rendering gate: table.ts :179–184 (`maxRows === 0` ⇒ chart appended).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "renderScatterPlot bucketSize medianResult reservedForRecent", limit: 10 });
```

## Verdict
Adopt the stratified sampling shape and median-representative rule verbatim for any long-run visualization; adapt glyphs/dimensions; omit axis-label reconstruction only if your host renders real axes. Coverage caveat: untested directly — source-pinned.
