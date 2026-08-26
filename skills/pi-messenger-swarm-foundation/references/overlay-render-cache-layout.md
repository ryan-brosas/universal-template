<!-- capsule-v2 -->
# Overlay render cache & layout budget — how does a full-screen TUI redraw at interactive rates over live files?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** Which caching and height-budgeting tricks make the overlay cheap to re-render?

## 50ms keyed cache + panel-height arithmetic + feed-window sync
**Path/Symbol:** `overlay/component.ts:RENDER_CACHE_TTL_MS = 50` (:52) with `buildRenderCacheKey` consumer; `overlay/feed-window.ts:getFeedLineCountCached` (:21), `calculateBasePanelHeights` (:42), `estimateFeedViewportHeight` (:75), `ensureFeedWindowInitialized` (:107), `syncFeedWindow` (:149); `overlay/render-layout.ts:calculateListLayout` (:38).
**Signature:** `syncFeedWindow(options): void` reconciles loaded event window against viewport demand.
**Data Shape:** cache key composes state identity (channel, view mode, selection, sizes); FeedLineCountCache memoizes per-channel rendered line counts.

### Decisive source
```ts
const RENDER_CACHE_TTL_MS = 50;
```
```ts
export function ensureFeedWindowInitialized(options: { ... }) {
  // seed the sparse absolute window from the tail so first paint never reads the whole log
}
```

**Flow:** every render tick builds a key; identical keys within 50ms return cached frame text. Panel heights derive from terminal rows minus fixed chrome (status bar, channel bar, input) with the feed getting remainder; scrolling near window edges triggers syncFeedWindow older/newer loads through scroll-core math; line-count caches avoid re-wrapping unchanged events.
**Invariant:** Cache TTL is deliberately SHORTER than the live-progress notify throttle (100ms) so worker updates invalidate promptly while keystroke bursts collapse — porters who lengthen it freeze live status; who shorten it burn CPU re-rendering.
**Probe:** direct tests `tests/swarm/overlay-snapshot.test.ts`, `tests/feed-scroll.test.ts` (window math), `tests/mention-autocomplete.test.ts` (input path); `grep -c "RENDER_CACHE_TTL_MS = 50" overlay/component.ts` (=1); `grep -n "buildRenderCacheKey" overlay/component.ts overlay/feed-window.ts | head -3`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "RENDER_CACHE_TTL buildRenderCacheKey calculateBasePanelHeights syncFeedWindow ensureFeedWindowInitialized", limit: 6 });
```

## Verdict
Adopt short-TTL keyed frame caching + viewport-arithmetic layout + sparse-window sync for file-backed TUIs; adapt budgets; omit if your UI framework already diffs frames.
