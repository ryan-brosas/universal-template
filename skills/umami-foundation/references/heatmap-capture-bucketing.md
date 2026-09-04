<!-- capsule-v2 -->
# Heatmap capture & scroll-depth bucketing — how do you collect clicks/scroll depth with page-dimension snapshots and aggregate them into renderable buckets?

**Source:** umami v3.3.1 / MIT @ master`ca661c70`; Codebase Memory `ext-umami`. **Question:** How are click coordinates normalized against changing page dimensions, and how does scroll depth become per-viewport buckets?

## heatmap-capture-bucketing
**Path/Symbol:** sender `src/recorder/index.js:beginHeatmapCapture :447-634 (onClick :487-566, onScroll :569-581, flushScroll :468-486)`; ingest `src/app/api/record/route.ts:223-248`; aggregation `src/queries/sql/heatmap/getHeatmap.ts:127-186 + pickScrollSnapshotViewport :684+`; save normalization `src/queries/sql/heatmap/saveHeatmapEvents.ts:toInt/toScrollPct`.
**Signature:** scroll event = max-scroll-pct-per-URL between flushes; SCROLL_BUCKET_SIZE=10; buckets keyed `(depth,pageW,pageH,viewportW,viewportH)`.
**Data Shape:** click rows carry BOTH viewport coords (x,y) and document coords (pageX,pageY) plus measured pageW/pageH at click time.

### Decisive source
```js
const onClick = event => {
  if (!event.isTrusted || event.button !== 0) return;         // synthetic/right-click rejected
  ...
  const pageX = Number.isFinite(event.pageX) ? event.pageX : event.clientX + scrollLeft;
  const pageW = Math.max(rawPageW, Math.ceil(pageX), Math.ceil(targetRight)); // widen page box to fit the click
  queueHeatmapEvent({ type:'click', x, y, pageX, pageY, pageW, pageH, viewportW, viewportH });
};
// server-side clamp:
function toScrollPct(value) { return Math.max(0, Math.min(100, Math.round(value))); }
```

**Flow:** clicks batch at 20 events / 5s; scroll tracks maxPct with a 400ms trailing debounce and only emits when it EXCEEDS the last flushed value → server clamps ints and pct → read side groups per visit (`max(scroll_pct)`), floors to 10-point buckets, and picks the snapshot viewport by max-session share.
**Invariant:** pageW/pageH are captured AT EVENT TIME (pages grow/shrink); widening the page box to include the click/target rect guarantees the point renders inside the overlay even when measurement raced layout. `isTrusted` filtering is what keeps scripted floods out. Scroll uses max-not-latest because users scroll up.
**Probe:** structural pins: `grep -n "SCROLL_BUCKET_SIZE" src/queries/sql/heatmap/getHeatmap.ts | head -1` → :18; `grep -c "Math.min(100" src/queries/sql/heatmap/saveHeatmapEvents.ts src/recorder/index.js` → ≥1 line each file.
**Probe:** `grep -n "isTrusted" src/recorder/index.js` → :488.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "ext-umami", query: "queueHeatmapEvent scrollPct computePageMetrics bucket", limit: 10 });
```
**(Retrieve:)**

## Verdict
Adopt event-time dimension capture + max-scroll tracking + fixed-bucket aggregation for heatmaps; adapt bucket size and debounce; omit iframe snapshot resolution if you render overlays differently.
