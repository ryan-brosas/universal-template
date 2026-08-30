<!-- capsule-v2 -->
# Feed scroll window math — how does an infinite log render in a finite viewport without losing your place?

**Source:** pi-messenger-swarm MIT `main@6fe429a4b74ae276a621bb72910d7926fb6b3104`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm`. **Question:** What is the pure scroll-state machine behind the overlay feed?

## Line-offset scroll over a sparse absolute window
**Path/Symbol:** `feed/scroll-core.ts` — `FeedScrollState` (:11-26), `maintainScrollOnNewEvents` (:83-105), `calculateVisibleRangeFromLines` (:146-194), `initializeScrollState` (200-event initial window :132-140).
**Signature:** `calculateVisibleRangeFromLines(allLines, lineScrollOffset, feedHeight, windowStart, totalLines)` → `{visibleLines, clamped offset, needsOlderLoad, needsNewerLoad}`.
**Data Shape:** two coordinate systems: ABSOLUTE event index in the channel jsonl (feedWindowStart/End sparse loaded range) vs RENDERED line offsets from bottom (0 = newest visible).

### Decisive source
```ts
export function maintainScrollOnNewEvents(
  currentOffset, wasAtBottom, previousRenderedLines, newRenderedLines, feedHeight
): number {
  if (wasAtBottom) return 0;                       // follow tail
  const linesAdded = newRenderedLines - previousRenderedLines;
  const newOffset = currentOffset + linesAdded;    // shift view by growth to hold position
  const maxOffset = Math.max(0, newRenderedLines - feedHeight);
  return Math.min(newOffset, maxOffset);
}
```
```ts
// Need older if we're showing the first few lines of what's loaded
const needsOlderLoad = lineStart < 5 && windowStart > 0;
```

**Flow:** init loads last ≤200 events at offset 0 (bottom); scrolling up grows lineScrollOffset against max = totalRendered−viewport; new events either snap you back to 0 (wasAtBottom) or add their count to your offset so content appears to stay put; approaching within 5 lines of the loaded window's top triggers an older-load that EXTENDS the absolute window backwards (window trim rule: keep total ≤ windowSize by cutting the newer side).
**Invariant:** Offset is measured from the BOTTOM of rendered lines, so "hold position under append" means INCREASING offset by linesAdded — sign errors here make history jump while reading. needsNewerLoad is near-dead by construction (auto-follow covers it) and pinned as such.
**Probe:** direct tests `tests/feed-scroll.test.ts` (pure-function suites over maintainScrollOnNewEvents/calculateVisibleRangeFromLines; `grep -n "describe(" tests/feed-scroll.test.ts | head -3`) and `tests/feed.test.ts::readFeedEvents caches...`; `grep -c "lineStart < 5" feed/scroll-core.ts` (=1).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-messenger-swarm", query: "maintainScrollOnNewEvents calculateVisibleRangeFromLines initializeScrollState needsOlderLoad", limit: 5 });
```

## Verdict
Adopt dual-coordinate (absolute-window × bottom-relative-offset) scroll math verbatim for any growing-log viewer; adapt window sizes; omit newer-load machinery if appends always auto-follow.
