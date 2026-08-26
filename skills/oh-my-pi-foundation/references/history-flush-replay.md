<!-- capsule-v2 -->
# history-flush-replay — how do graceful shutdown and scrollback reset reuse the retirement machinery without corrupting lifecycle state?

**Source:** oh-my-pi MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What does `TUI.stop` do with pending finalized history, and how does replay re-offer committed rows without rewinding state?

## TUI stop/flush + beginHistoryReplay
**Path/Symbol:** `packages/tui/src/tui.ts` (`#flushHistoryBeforeStop`, `stop`, `#prepareForcedRender`) + composer/container `beginHistoryFlush` / `beginReplay`.
**Signature:** `beginHistoryFlush?(): void` and `beginHistoryReplay?(): void` on `TerminalFrameProvider` (renamed from `resetHistory` in this drift wave).
**Data Shape:** Flush loop: render frame → if `plan.history === undefined` done → emit plan frame → REQUIRE the offered batch id to be accepted (`throw new Error("History flush did not accept the offered batch")` otherwise) → repeat.

### Decisive source
```ts
provider.beginHistoryFlush();
while (true) {
	this.#imageBudget.beginPass();
	const plan = provider.renderFrame({ columns: width, rows: height });
	this.#imageBudget.endPass();
	if (plan.history === undefined) return;
	...
	if (plan.history.id > acceptedBefore && this.#acceptedHistoryBatchId === acceptedBefore) {
		throw new Error("History flush did not accept the offered batch");
	}
}
```

**Flow:** `stop()` runs the flush BEFORE alt-screen teardown so every finalized prefix lands in native scrollback; the loop terminates because each acceptance advances the provider's frontier until nothing eligible remains. Replay is the mirror path: a forced clear (`\x1b[3J` path) or resize replay calls `beginHistoryReplay`, which sets `#replayRequested` (deferred while an offer is outstanding) and walks the committed prefix back in one-block batches — replay offers carry fresh ids, are excluded from live-viewport accounting only as an independent stream, and acking them NEVER changes block states.
**Invariant:** Flush/replay change NOTHING about logical lifecycle: committed stays committed; replay just renders the immutable prefix again; the flush-loop guard turns a non-accepting provider into a loud error instead of silent data loss.
**Probe:** `grep -nF 'beginHistoryFlush(): void' packages/coding-agent/src/modes/composer.ts` → line `293` and `grep -nF 'peekFlushBatch(width)' packages/coding-agent/src/modes/composer.ts` → line `343`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "flushHistoryBeforeStop beginHistoryReplay TerminalFrameProvider resetHistory", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flush-before-teardown with the accept-or-throw guard; adapt to your terminal abstraction; omit kitty image-budget passes if you have no graphics protocol. Direct tests: `packages/tui/test/history-frame-plan.test.ts` "flushes every eligible history batch before terminal handoff" (acknowledged `[1, 2]`, both rows in buffer); welcome-history-resize "flushes a roomy finalized transcript before composer shutdown" (`settled` → `committed`).
