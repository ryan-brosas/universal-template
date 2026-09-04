<!-- capsule-v2 -->
# Web-vitals collection with CLS session windows & INP p98 — how do you compute Core Web Vitals by hand and when do you flush them?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are TTFB/FCP/LCP/CLS/INP computed from PerformanceObserver and what triggers the send?

## web-vitals-session-windows
**Path/Symbol:** `src/tracker/index.ts:initPerformance :438-637 (CLS :479-497, INP :500-527, flushPerformance :607-622)`.
**Signature:** observers: `navigation`(ttfb), `paint`(fcp), `largest-contentful-paint`(lcp), `layout-shift`(cls), `event` with `durationThreshold:40`(inp); flush on 10s timer, `visibilitychange→hidden`, `pagehide`, and SPA route push.
**Data Shape:** metrics {ttfb,fcp,lcp,cls,inp,duration}; all clamped ≥0 via `Math.max(x - activationStart, 0)`.

### Decisive source
```ts
// CLS — session-window algorithm: gap < 1s extends, window < 5s total, report WORST window
if (lastEntry && entry.startTime - lastEntry.startTime - lastEntry.duration < 1000 &&
    entry.startTime - firstEntry.startTime < 5000) {
  clsSessionValue += entry.value; clsSessionEntries.push(entry);
} else { clsSessionValue = entry.value; clsSessionEntries = [entry]; }
if (clsSessionValue > (metrics.cls || 0)) metrics.cls = clsSessionValue;

// INP — max duration per interactionId, then ~98th percentile
const p98Index = Math.floor(Math.max(values.length, 10) * 0.02);
metrics.inp = values[Math.min(p98Index, values.length - 1)];
```

**Flow:** buffered observers catch pre-script entries → route change (`flushPerformance`) sends current window then RESETS all accumulators and starts a new 10s timer → hidden/pagehide final-send guarded by `sent` flag.
**Invariant:** the `Math.max(values.length, 10)` floor means small samples use near-max instead of a noisy p98 — dropping it makes INP jumpy on quiet pages. `hadRecentInput` shifts are excluded from CLS. The sent-flag reset inside flush is what allows ONE metric payload per route view.
**Probe:** structural pins: `grep -n "durationThreshold" src/tracker/index.ts` → :521; `grep -c "hadRecentInput" src/tracker/index.ts` → 2; `grep -n "0.02" src/tracker/index.ts` → :526.
**Probe:** `grep -n "visibilitychange" src/tracker/index.ts | wc -l` → 2.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "initPerformance layout-shift largest-contentful-paint interactions", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt hand-rolled vitals when you can't ship web-vitals lib (tracker-size budget); adapt thresholds to your spec version; omit fallback getEntriesByType path if observers always available.
