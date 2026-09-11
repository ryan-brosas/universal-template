<!-- capsule-v2 -->
# Dual-plane output truncation — why do the LLM and the human get different windows of benchmark output?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** How is long-running command output bounded for the model while keeping the full log reachable?

## truncateTail + streaming spill — 10 lines/4KB to the LLM, full output to a temp file
**Path/Symbol:** `harness/server.ts` — `truncateTail` :378–425; constants `EXPERIMENT_MAX_LINES=10` / `EXPERIMENT_MAX_BYTES=4*1024` :82–83, `DEFAULT_MAX_LINES=2000` / `DEFAULT_MAX_BYTES=50*1024` :375–376; stream-spill :985–1023; dual truncation :1110–1129.
**Signature:** `truncateTail(text, {maxLines?, maxBytes?}): { content, truncated, truncatedBy: 'lines'|'bytes'|null, totalLines, outputLines }`.
**Data Shape:** in-memory ring of Buffer chunks capped at `2×DEFAULT_MAX_BYTES` (100KB) with newline-aligned head-trim; once total exceeds 50KB the WHOLE stream spills to `/tmp/pi-experiment-<hex>.log`.

### Decisive source
```ts
const llmTruncation = truncateTail(output, {
  maxLines: EXPERIMENT_MAX_LINES,   // 10
  maxBytes: EXPERIMENT_MAX_BYTES,   // 4 KiB
});
// ...
text += `\n${llmTruncation.content}`;
if (llmTruncation.truncated) {
  // "[Showing last N of M lines." / "(4KB limit)." + " Full output: <tempfile>]"
}
```

**Flow:** child stdout/stderr → `handleData`: totals tracked; crossing DEFAULT_MAX_BYTES lazily opens the temp file and back-writes buffered chunks (allocator memoized via closure so the path exists exactly once per run); in-memory chunks trimmed oldest-first but always cut at a NEWLINE boundary (`indexOf(0x0a)`), never mid-line. On close: bytes-first truncation inside truncateTail drops whole leading lines until under budget, then line-count truncation keeps the LAST maxLines. The LLM sees ≤10 tail lines + a pointer to the full file; METRIC parsing runs on the UNTRUNCATED string (`parseMetricLines(output)` :1132), so metrics can never be truncated away.
**Invariant:** metric extraction happens BEFORE/WITHOUT any truncation window — a porter who parses the LLM-facing text loses metrics whenever output is long. Tail-keeping (not head) is deliberate: benchmark conclusions (METRIC lines, final status) print last. `truncatedBy` distinguishes which bound fired so the pointer message is truthful. Checks output gets its own separate cap (last 80 lines shown).
**Probe:** anchors: `grep -n 'appendFileSync' harness/server.ts | grep -c 'pi-experiment'` → 0 (spill uses createWriteStream, not append); `grep -n 'EXPERIMENT_MAX_LINES\|EXPERIMENT_MAX_BYTES' harness/server.ts | wc -l` → ≥5 sites (:82–83 consts, :1115 spill condition, :1127–1128 llm call); `grep -n 'chunksBytes > maxChunksBytes' harness/server.ts` → :1011 + :1015 (ring trim loop).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "truncateTail tempFileStream chunksBytes EXPERIMENT_MAX_BYTES", limit: 10 });
```

## Verdict
Adopt the two-budget design (tight LLM window + durable full-log file) and parse-metrics-from-untruncated invariant verbatim; adapt budgets/temp paths to host; omit the Windows-specific byte accounting only with a documented reason. No direct vitest drives truncateTail — source-pinned.
