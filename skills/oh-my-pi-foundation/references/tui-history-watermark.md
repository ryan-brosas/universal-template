<!-- capsule-v2 -->
# TUI history watermark — how does the terminal layer append exactly-once scrollback batches and drain a shutdown flush without accepting anything twice?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the accepted-id watermark protocol in `#emitPlanFrame`, and how does `#flushHistoryBeforeStop` guarantee every eligible batch lands before terminal handoff?

## Watermark + anchored write
**Path/Symbol:** `packages/tui/src/tui.ts:` `#acceptedHistoryBatchId = 0` (:633), `#providerViewportTop` (:635), `#flushHistoryBeforeStop` (:1345–1365), `stop()` call site (:1386), `#prepareResizeReplay` (:2000–2023), `#emitPlanFrame` (:2031–2176, ack+drain at :2045–2046/:2168–2175).
**Signature:** `#emitPlanFrame(width, height, viewportRows, offered: HistoryBatch | undefined, provider)`: void; provider contract `acknowledgeHistory(id)` + optional `beginHistoryReplay()` / `beginHistoryFlush()`.
**Data Shape:** Frame plan `{ history?: HistoryBatch; viewport: string[] }`; stale offer (`id <= watermark`) is dropped AND immediately acknowledged.

### Decisive source
```ts
const history = offered !== undefined && offered.id > this.#acceptedHistoryBatchId ? offered : undefined;
if (offered !== undefined && offered.id <= this.#acceptedHistoryBatchId) provider?.acknowledgeHistory(offered.id);
...
// viewport stays anchored directly below whatever history remains; appending K
// rows scrolls at most K rows off the top — the oldest visible history:
const newTop = Math.max(0, Math.min(startTop + historyRows.length, height - rows));
...
if (history !== undefined) {
	this.#acceptedHistoryBatchId = history.id;
	provider?.acknowledgeHistory(history.id);
	// Draining is one batch per frame … Pump the next frame instead of waiting.
	this.requestRender();
}
```

**Flow:** render → plan.history accepted only if strictly newer than the watermark → non-diffable path writes history rows from `startTop` then the viewport below, erasing old live rows first so "a scroll can only push committed rows and blanks, never an unfinished frame" (:2103–2111) → after write: bump watermark, ack provider, self-`requestRender()` to pump multi-batch drains. Shutdown: `stop()` → `#flushHistoryBeforeStop()` loops `beginHistoryFlush()` + frame + emit until the provider stops offering, throwing `"History flush did not accept the offered batch"` if an emitted newer batch failed to move the watermark (:1359–1363).
**Invariant:** Exactly-once append is enforced by the WATERMARK on the consumer side even though providers also dedupe by id — belt-and-suspenders across provider swaps/replays. The anchor (`#providerViewportTop`) moves down K with every append so live rows are never repainted over history. Flush-before-stop runs AFTER alt-screen exit sequences but BEFORE the final cursor-park writes, so flushed rows are real scrollback bytes. Resize replay latches per size string (`#resizeReplaySize`) to fire once per geometry change; `preserve` mode never replays; rebuild mode defers through the destructive-reset latch so ED3 clears stale history before the same replay.
**Probe:** `packages/tui/test/history-frame-plan.test.ts` — `"flushes every eligible history batch before terminal handoff"` pins acks `[1, 2]` after stop; `"appends finalized history once…"` pins `baseY=1` single-append; replay twins pin resize modes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "acceptedHistoryBatchId emitPlanFrame acknowledgeHistory", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `#flushHistoryBeforeStop tui.ts:1345-1365`; ack/drain verified byte-exact at `tui.ts:2168-2175`.

## Verdict
Adopt the monotonic-watermark + acknowledge-after-write handshake for any host-side append into an immutable log; keep erase-before-scroll so unfinished frames can't reach scrollback. Adapt the ANSI specifics; preserve the flush loop's failure throw (a silent partial flush would strand transcript content). Runner caveat as recorded for this repo.
