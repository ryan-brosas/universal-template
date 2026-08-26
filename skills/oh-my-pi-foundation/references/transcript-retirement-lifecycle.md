<!-- capsule-v2 -->
# Transcript retirement lifecycle — how do finished transcript blocks move into immutable terminal scrollback without ever repainting or losing a row?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the exact active→settled→committed state machine, and when does each retirement policy (`pressure` vs `flush`) offer a prefix batch?

## Offer-based prefix retirement
**Path/Symbol:** `packages/coding-agent/src/modes/components/transcript-container.ts:` `BlockState` (:28), `MAX_LIVE_BLOCKS = 256` (:43), `peekFinalizedBatch` (:213–215), `peekFlushBatch` (:218–220), `#peekBatch(width, capacity, policy)` (:222–270), `acknowledgeFinalizedBatch(id)` (:273–289).
**Signature:** `peekFinalizedBatch(width: number, capacity: number): HistoryBatch | undefined; peekFlushBatch(width: number): HistoryBatch | undefined; acknowledgeFinalizedBatch(id: number): void`.
**Data Shape:** `HistoryBatch { id: number; rows: readonly string[] }`; internal offer `{ batch, end, kind: "commit" | "replay" }`; lifecycle doc-comment: committed rows are "immutable terminal history … never re-rendered" (:26).

### Decisive source
```ts
const overflowing = total > room || this.#liveCount() >= MAX_LIVE_BLOCKS;
if (policy === "pressure" && !overflowing) return undefined;      // flush ignores room
let end = this.#frontier;
while (end < this.#entries.length && this.#entries[end]!.state === "settled") {
	if (policy === "pressure" && total - freed <= room
		&& this.#liveCount() - (end - this.#frontier) < MAX_LIVE_BLOCKS) break;
	freed += heights[index]! > 0 ? heights[index]! + 1 : 0;
	end++; index++;
}
if (end === this.#frontier) return undefined;
this.#offered = { batch: { id: this.#nextBatchId++, rows: this.#renderRange(this.#frontier, end, width) }, end, kind: "commit" };
```

**Flow:** every public query runs `#syncEntries()` (rebuild from container children, recompute frontier = first non-committed, :376–386) then `#settleFinalized()` (active blocks whose component reports `isTranscriptBlockFinalized()` become settled; components without the hook finalize immediately, :46–49/:353–357) → measure live heights at current width → pressure policy offers only when rows overflow capacity OR live count hits 256; flush policy (capacity 0) always offers the complete eligible settled prefix → offer stands until acknowledged; a second peek returns the SAME batch (`#offered !== undefined` short-circuit :225).
**Invariant:** Retirement is OFFER-then-ACKNOWLEDGE, never immediate: blocks stay live (still reflowing to the current width on resize) until the TUI writes the rows into native scrollback and acknowledges by id. Commit order is absolute — the scan stops at the first still-active block, so a slow streaming block pins everything behind it in the viewport. Acknowledging a non-offered id is a silent no-op; acknowledging flips exactly `frontier..end` to committed and bumps frontier. An unacknowledged offered batch also fences `canRemoveBlock` (removal inside `[frontier, end)` is refused — mid-write desync, :107–118).
**Probe:** `packages/coding-agent/test/modes/components/transcript-container.test.ts` — `"flushes a finalized prefix without viewport pressure"` pins `peekFinalizedBatch(80,10)` undefined vs `peekFlushBatch(80)` = `["fits", ""]`; `"appends finalized history once…"` (tui suite) pins single-append.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "TranscriptContainer peekFinalizedBatch settled committed", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `peekFinalizedBatch transcript-container.ts:213-215`, `beginReplay :132-139`.

## Verdict
Adopt offer/acknowledge retirement with a monotonic batch-id handshake for any "viewport + native scrollback" split; adapt row rendering to your component model but keep settle-before-measure (heights must come from final content). Omit nothing behavioral: the stop-at-first-active rule and the offered-batch removal fence are what prevent torn transcripts. Runner caveat: bun test blocked here by pi-natives nightly build (recorded [DONE:454] class); probes byte-exact at pin.
