<!-- capsule-v2 -->
# transcript-block-lifecycle — what is the exact active→settled→committed state machine, and which operations may touch each state?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** How does a transcript block become immutable terminal history, and when is removal refused?

## TranscriptContainer
**Path/Symbol:** `packages/coding-agent/src/modes/components/transcript-container.ts` (`TranscriptContainer`, `BlockState`, `#peekBatch`, `acknowledgeFinalizedBatch`, `canRemoveBlock`).
**Signature:** `peekFinalizedBatch(width, capacity): HistoryBatch | undefined`; `peekFlushBatch(width)`; `acknowledgeFinalizedBatch(id: number)`; `canRemoveBlock(component): boolean`.
**Data Shape:** `BlockState = "active" | "settled" | "committed"`; offer `{ batch, end, kind: "commit" | "replay" }`; `MAX_LIVE_BLOCKS = 256`.

### Decisive source
```ts
while (end < this.#entries.length && this.#entries[end]!.state === "settled") {
	if (
		policy === "pressure" &&
		total - freed <= room &&
		this.#liveCount() - (end - this.#frontier) < MAX_LIVE_BLOCKS
	)
		break;
	freed += heights[index]! > 0 ? heights[index]! + 1 : 0;
	end++;
	index++;
}
```

**Flow:** `#settleFinalized` promotes any `active` block whose `isTranscriptBlockFinalized?.() ?? true` says done → under pressure (or flush), the LONGEST settled prefix starting at `#frontier` that frees enough room becomes an offered batch; the offer stands unacknowledged-or-reoffered (`#peekBatch` returns the same batch while offered) → `acknowledgeFinalizedBatch(id)` marks exactly `[frontier, end)` committed and advances the frontier. Retirement stops at the first still-active block because commit order is absolute.
**Invariant:** Committed blocks never render again and are removal-refused; blocks inside an offered-but-unacked batch are mid-write and also refusal-protected (`canRemoveBlock`: `this.#offered === undefined || index >= this.#offered.end`); a wrong id acks nothing.
**Probe:** `grep -nF 'state === "settled"' packages/coding-agent/src/modes/components/transcript-container.ts` → line `252` and `grep -cF 'MAX_LIVE_BLOCKS = 256' packages/coding-agent/src/modes/components/transcript-container.ts` → `1`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "TranscriptContainer peekFinalizedBatch acknowledgeFinalizedBatch frontier settled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-state machine + offer/ack two-phase commit; adapt row rendering; omit the emergency one-row-per-block path if your viewport never overflows block count. Direct test: `packages/coding-agent/test/modes/components/transcript-container.test.ts` — pressure ordering, no-successor-past-active, reoffer-idempotence, same-frame exclusion, removal ladder.
