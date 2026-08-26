<!-- capsule-v2 -->
# composer-history-offer — how does the composer translate per-container batch ids into one monotonic history the terminal watermark can trust?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** When is the header offered vs transcript batches, and how do acks/replays chain without double-painting rows?

## Composer renderFrame / #offerHistory
**Path/Symbol:** `packages/coding-agent/src/modes/composer.ts` (`Composer.renderFrame`, `#offerHistory`, `acknowledgeHistory`).
**Signature:** `renderFrame(viewport: ViewportSize): TerminalFramePlan` returning `{ history?: { id, rows }, viewport }`; `#offerHistory(transcript, width, rows, chromeRows)`.
**Data Shape:** Composer-owned `#nextHistoryId` (monotonic across container clears/swaps); `#offeredHistory.source = "header" | "headerReplay" | { transcript, transcriptId }`.

### Decisive source
```ts
// Offer history under capacity pressure only: blocks stay live (and keep
// reflowing to the current width) while the screen has room. A batch
// leaves the mutable viewport in the same frame it is appended, so its
// rows are never painted twice.
const history = this.#offerHistory(transcript, width, rows, preRoots.length + after.length);
```
with the header gate one layer down:
```ts
if (!this.#historyFlush && renderedHeader.length + chromeRows + liveRows <= rows) return undefined;
```

**Flow:** Header retires FIRST once the screen fills (or on flush); its acceptance stores `#retiredHeaderRows` — exact hard rows that resize-alt frames reflow rather than recompose. Transcript batches are then offered one at a time; `acknowledgeHistory(id)` matches the pending offer's id exactly and forwards to `transcript.acknowledgeFinalizedBatch`, so container-local ids never leak to the terminal. A batch leaves the live viewport the same frame its rows are appended to history (`#liveEntries()` starts after `offered.end`) — no double paint, no gap.
**Invariant:** One outstanding offer at a time; ids strictly increase; an unaccepted offer is re-returned verbatim on later frames; header-visible logic (`!this.#headerRetired && source !== "header"`) keeps the retiring header on its final frame.
**Probe:** `grep -nF 'renderedHeader.length + chromeRows + liveRows <= rows' packages/coding-agent/src/modes/composer.ts` → line `331` and `grep -cF '#historyReplayRequested' packages/coding-agent/src/modes/composer.ts` → `4`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "Composer offerHistory nextHistoryId headerReplay transcript batch", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pressure-gated retirement + monotonic id translation; adapt the frame-plan plumbing to your renderer; omit multiplexer-specific reflow if you never resize. Direct test: `packages/coding-agent/test/welcome-history-resize.test.ts` (exactly-one welcome row through 40 repaints + 5 resizes; editor rectangle anchor at viewport row 9).
