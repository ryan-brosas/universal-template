<!-- capsule-v2 -->
# Transcript replay without rewind — how does a terminal re-print the whole committed history after a resize without corrupting retirement state?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How does `beginReplay` re-offer committed blocks as NEW batches while keeping lifecycle state frozen, and how do replay batches coexist with live viewport pressure?

## Replay cursor over committed prefix
**Path/Symbol:** `packages/coding-agent/src/modes/components/transcript-container.ts:` `beginReplay` (:131–139), `#startReplay` (:319–323), replay arm of `#peekBatch` (:226–232), replay arm of `acknowledgeFinalizedBatch` (:281–286), `#liveEntries` (:359–363), `#replayRequested` latch (:71).
**Signature:** `beginReplay(): void` (container); `#replay: { cursor: number; end: number } | undefined`.
**Data Shape:** Replay = `{cursor, end}` window over `[0, #frontier)`; replay offers carry `kind: "replay"`; one block per offer (`end = Math.min(start + 1, this.#replay.end)`).

### Decisive source
```ts
// #peekBatch, before any pressure math — replay preempts retirement offers:
if (this.#replay !== undefined) {
	const start = this.#replay.cursor;
	const end = Math.min(start + 1, this.#replay.end);
	const batch = { id: this.#nextBatchId++, rows: this.#renderRange(start, end, width) };
	this.#offered = { batch, end, kind: "replay" };
	return batch;
}
// acknowledge, replay arm — advance cursor; NEVER touch entry states:
const replay = this.#replay;
if (replay === undefined || offered.end > replay.end) return;
replay.cursor = offered.end;
if (replay.cursor === replay.end) this.#replay = undefined;
```

**Flow:** `beginReplay()` while an offer is outstanding only sets `#replayRequested`; otherwise `#startReplay()` sets `{cursor:0, end:#frontier}` (undefined when nothing committed) → subsequent peeks emit ONE rendered block per frame as a fresh batch id → ack advances the cursor until the window drains. The TUI's settled-resize hook (`#prepareResizeReplay` :2000–2023) calls `beginHistoryReplay()` in append mode (current-width copy written below retained history) or routes rebuild mode through the ED3 destructive-reset latch first.
**Invariant:** Replay NEVER rewinds state — the pass-1-era `resetRetirement()` that flipped committed→settled was deliberately removed ("decouple replay state from finalized lifecycle state, preventing accidental re-activation"); a test pins states stay `["committed"]` after begin+peek+ack and `peekFinalizedBatch(80,0)` stays undefined afterward. While replay is active, `#liveEntries()` excludes only an offered COMMIT (`kind === "commit"` uses `offered.end`) but never a replay — so live rendering and capacity pressure continue independently underneath. Re-request during drain re-arms via the two latches (`#replayRequested` container-side, `#historyReplayRequested` composer-side) instead of queueing a second window.
**Probe:** `packages/coding-agent/test/modes/components/transcript-container.test.ts` — `"replays committed history without rewinding lifecycle state"`, `"keeps the live viewport while an independent replay is offered"` (replay rows `["committed",""]` while viewport shows `["active"]`); tui suite `"appends a current-width replay after settled resize"` / `"rebuilds current-width history without retaining stale rows"` pin both resize modes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "peekFlushBatch beginReplay TranscriptContainer", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `beginReplay transcript-container.ts:132-139`, `peekFlushBatch :218-220`.

## Verdict
Adopt the frozen-state replay cursor whenever committed output must be re-emitted at a new width; keep one-block-per-frame pacing so a giant transcript cannot monopolize frames. Adapt trigger wiring to your resize handling; preserve the append-vs-rebuild distinction (append duplicates rows below retained history; rebuild must erase native history FIRST). Runner caveat as in sibling capsules.
