<!-- capsule-v2 -->
# Live bench board — how does a benchmark CLI render a concurrent per-model progress board that degrades to parseable lines when stdout is piped?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@2b66ee69f2`; Codebase Memory `oh-my-pi`. **Question:** What is the observer→board contract, and what are the TTY vs non-TTY output rules?

## Observer-driven dual rendering
**Path/Symbol:** `packages/coding-agent/src/if-bench/board.ts:` `IfBenchBoard` (:32–38), `createIfBenchBoard` (:63–117), `renderLive` (:119–144), `ladder` meter (:151–162), `formatVerdict`/`failureDetail` (:176–200), `formatIfBenchScoreboard` (:221–259); shared `createLiveBoard` from `../cli/live-board`.
**Signature:** `createIfBenchBoard(meta, output = process.stdout, errors = process.stderr): IfBenchBoard` implementing `IfBenchObserver` (`modelStarted/turnStarted/turnFinished/modelFinished`) + `log/close`.
**Data Shape:** `RowState {startedAt, turn, actions, passed, failed, placement, lastDurationMs}` keyed by model label; ladder width 28 cells scaled to maxTurns.

### Decisive source
```ts
turnFinished(label, record) {
	const row = rows.get(label);
	if (row) { ...; if (record.passed) row.passed = record.turn; else row.failed = true; board.repaint(); }
	if (!board.interactive) {
		const sink = record.passed ? output : errors;
		sink.write(`${formatTurnLine(label, record)}\n`);   // piped stdout stays a clean trace
	}
},
modelFinished(report) {
	rows.delete(report.label);                 // settled models leave the live area
	board.log(formatVerdict(report, meta));    // and gain a permanent verdict line
	if (report.failure) for (const line of failureDetail(report)) board.log(line);
}
```

**Flow:** each model gets one live row: filled `█` cells per passed turn, spinner cell for in-flight, dim `░` remainder (`▚` marks failed), plus `cat@placement` and cumulative actions → on finish the row is REMOVED from the live map and a permanent verdict line logs above (expected/actual pair clipped to 120 cols for the broken turn). Scoreboard ranks depth-first — turns, then actions, latency ONLY as tie-break ("surviving one more turn always beats answering faster") — with the leader line green.
**Invariant:** Non-TTY mode writes pass-lines to stdout and fail-lines to stderr so scripted callers get a parseable turn-by-turn trace without ANSI churn. Live rows must be deleted on finish or the live area grows unbounded across many models. The observer hooks are all optional downstream (JSON mode passes none) — the board is a pure consumer.
**Probe:** No dedicated unit test drives the board (interactive rendering); behavior verified by read at pin: non-TTY sink split @board.ts:103–106, rows.delete @:109, tie-break chain @:223. Deterministic greps: `FAILURE_TEXT` five-kind table @:23–29, `LADDER_WIDTH = 28` @:18. Runner caveat as recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "runIfBench providerSessionState promptCacheKey", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @2b66ee69 via runner-plane query (`board.ts` methods are graph-visible under the if-bench family; `ladder formatIfBenchScoreboard` resolves through search_code for doc-shaped nodes).

## Verdict
Adopt live-rows-plus-permanent-verdicts for any concurrent benchmark UI; keep the stdout/stderr pass/fail split in non-TTY mode. Adapt the meter glyphs to your theme. Omit cost/token columns if your runs don't price them.
