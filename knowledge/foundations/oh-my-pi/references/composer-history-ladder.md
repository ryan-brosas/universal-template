<!-- capsule-v2 -->
# Composer history offer ladder — how does one app translate per-container batch ids into a single ordered native-history stream with the welcome header retiring first?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the composer-side arbitration that decides WHICH history batch (header, header replay, or any transcript's) is offered each frame, and why does it re-id everything?

## Id-translation + priority ladder
**Path/Symbol:** `packages/coding-agent/src/modes/composer.ts:` `#nextHistoryId` (:125), `#offeredHistory` union (:126–132), `renderFrame` (:199–242), `acknowledgeHistory` (:244–259), `beginHistoryReplay`/`beginHistoryFlush` (:283–295), `#startHistoryReplay` (:297–303), `#offerHistory` (:305–352).
**Signature:** `#offerHistory(transcript: TranscriptContainer, width: number, rows: number, chromeRows: number): { id: number; rows } | undefined`; `acknowledgeHistory(id: number): void`.
**Data Shape:** Offer source = `"header" | "headerReplay" | { transcript: TranscriptContainer; transcriptId: number }`; composer-owned monotonic `#nextHistoryId` independent of container batch ids.

### Decisive source
```ts
if (!this.#headerRetired) {
	const welcome = this.#welcome;
	if (welcome !== undefined && !welcome.isTranscriptBlockFinalized()) return undefined;
	const renderedHeader = this.#header.render(width);
	if (renderedHeader.length > 0) {
		const liveRows = transcript.liveRowCount(width);
		if (!this.#historyFlush && renderedHeader.length + chromeRows + liveRows <= rows) return undefined;
		this.#offeredHistory = { id: this.#nextHistoryId++, rows: [...renderedHeader, ""], source: "header" };
		return ...;
	}
	this.#headerRetired = true; this.#retiredHeaderRows = [];      // empty header retires silently
}
const batch = this.#historyFlush
	? transcript.peekFlushBatch(width)
	: transcript.peekFinalizedBatch(width, Math.max(0, rows - chromeRows));
```

**Flow:** every frame: outstanding offer is re-returned unchanged → pending header REPLAY preempts (`#reflowRetiredHeader(width, 0)` as `source:"headerReplay"`) → unretired header waits until the intro finalizes AND (screen full OR flush) then retires FIRST so transcript prefixes can follow in order → transcript asked via flush or pressure peek → returned batch is re-wrapped under a composer id and only then lands in the frame plan. `renderFrame` computes `#retiredHeaderStart` from visible-vs-offered header rows so resize-alt repaints can restore the anchor.
**Invariant:** The comment at :122–124 is the contract: "Transcript batch ids restart across container clears/swaps; the composer translates them into one monotonic sequence the terminal's accepted-id watermark can trust." Ack routing is by source shape: header ack stores `#retiredHeaderRows`, headerReplay ack clears `#headerReplayPending` + stores rows, transcript ack DELEGATES `transcript.acknowledgeFinalizedBatch(transcriptId)` — never conflate the two id spaces. A queued replay request fires only after the current offer resolves (`#historyReplayRequested` → `#startHistoryReplay()` at ack tail). Header retirement happens exactly once; empty-render headers flip to retired without an offer.
**Probe:** `packages/coding-agent/test/welcome-history-resize.test.ts` — `"flushes a roomy finalized transcript before composer shutdown"` (:282) pins stop-time flush flipping blockStates `["settled"]→["committed"]` with rows in the terminal buffer.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "offerHistory beginHistoryFlush acknowledgeHistory composer", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69: `#offerHistory composer.ts:306-352`, `beginHistoryFlush :293-295`, `acknowledgeHistory :245-259`.

## Verdict
Adopt single-writer id translation whenever multiple producers feed one ordered sink; keep the header-first ordering (it preserves "banner above transcript" in scrollback). Adapt the offer cadence to your frame loop; preserve re-return-outstanding-offer semantics — two offers in flight would break the watermark. Omit multiplexer-specific header reflow (`#reflowRetiredHeader`) unless you own hard-row scrollback too.
