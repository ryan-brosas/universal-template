<!-- capsule-v2 -->
# Mnemonic recall — signals, tiers, never-empty fallback; sleep consolidation

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Path:** `packages/mnemopi/src/core/beam/recall.ts` + `consolidate.ts` (+ `helpers.ts`). **Question:** How does a hybrid memory recall fuse FTS/dense/keyword/importance signals without ever returning empty, and how do old working memories become episodic summaries?

## Recall = fused signals, tier-aware scoring, honest previews
**Path/Symbol:** `packages/mnemopi/src/core/beam/recall.ts:recall` (946–997), `recallEnhanced` (1032), `type CandidateSignals` (34), `VERACITY_WEIGHTS` (61–71), `clipRecallContent` (88–98); scoring core `scoreCandidate` (~700s).
**Signature:** `recall(beam, query, topK = 40, options): Promise<RecallResult[]>` — options take `temporalWeight`, `vecWeight`, `ftsWeight`, `importanceWeight`, `queryEmbedding`, `useSynonyms/useIntent/useMmr`, `mmrLambda`, `contentPreviewChars`, `updateRecallCounts`, `source/topic/veracity/memoryType` filters.
**Data Shape:** sessions, spans, memory rows with FTS-friendly text columns, vector embeddings (binary/float BLOB); tiers `working|episodic`; veracity labels weighted (`stated:1.0 true:1.0 likely_true:1.0 unknown:0.8 inferred:0.7 imported:0.6 tool:0.5 false:0`).

### Decisive source
```ts
export const RECALL_CONTENT_PREVIEW_CHARS = 500;
export function clipRecallContent(content: string, limit = RECALL_CONTENT_PREVIEW_CHARS) {
  if (limit <= 0 || content.length <= limit) return { content, truncated: false, fullLength: content.length };
  return { content: `${content.slice(0, Math.max(0, limit-1))}…`, truncated: true, fullLength: content.length };
}
// scoreCandidate gate: relevance floor or strong dense signal, else dropped
if (lexical < minRel && candidate.signals.dense < 0.65) return null;
```

**Flow:** (1) `inferTemporalOptions` extracts a query time reference and defaults `temporalWeight=0.35`; "current"-asking queries set `queryTime`, `temporalWeight=0.45`, and `currentSensitive`; query embedding derives from text unless explicitly `null` (embeddings disabled ⇒ no-op) — (2) synonym-expanded tokens/groups + intent-classified weight adjustment over normalized weights — (3) candidate collection across FTS + dense (cosine on decoded embeddings) + lexical match — (4) tiered blend into one ±1 score: episodic rows take `max(dense·vecW + fts·ftsW + importance·impW, lexical·0.8)` then degradation tier weight (tier 1→1.0, 2→0.85, else 0.7); working rows take keyword-share + quadratic-keyword bonus with an 80/20 dense blend — (5) decay factor `score *= 0.7 + 0.3·decay` (72h default recency, or `temporalBoost` against query time), optional `score *= 1 + temporalWeight·temporalScore` with event-date boost at 2× half-life — (6) veracity weight × current-content adjustment — (7) sort, dedupe cross-tier summary links, coverage diversification when ≥4 tokens overflow topK, optional MMR (`mmrLambda ?? 0.7`) — (8) clip previews at 500 chars (trailing `…`, full length reported), update recall counts unless disabled.

**Invariant:** every numeric row field passes `asNumber` guards; a query never returns empty while the store has rows (fallback candidates carry `candidateSource: "fallback"`); previews always clip honestly — the full row stays reachable via `Mnemopi.get()` / `memory://<id>`.

**Probe:** `test/beam-recall-unit.test.ts`, `test/beam-e3-e4-e6.test.ts`, `test/beam-parity.test.ts`, `test/polyphonic-recall.test.ts` (engine purity), `test/recall-diagnostics.test.ts` (signal audit). Coverage caveat: tests excluded from graph index by design; probes source-grounded from on-disk files.

## Sleep consolidation — claim-then-summarize to episodic (HEAD shape)
**Path/Symbol:** `consolidate.ts:sleep` (972–1063), `sleepAllSessions` (1065–1122), `consolidateToEpisodic` (389–434).
**Signature:** `sleep(beam, dryRun = false): SleepResult`; `sleepAllSessions(beam, dryRun?): SleepResult`; `consolidateToEpisodic(beam, summary, sourceWmIds, source?, importance?, options?): string`.
**Data Shape:** `SleepResult { dry_run, status: "no_op"|"dry_run"|"consolidated", items_consolidated, summaries_created, session_results[], degradation?, … }`.

### Decisive source
```ts
const claimTs = isoNow();
beam.db.run(`UPDATE working_memory SET consolidated_at = ? WHERE id IN (${placeholders}) AND consolidated_at IS NULL`, [claimTs, ...ids]);
const claimed = new Set(asRows(beam.db.query(
  `SELECT id FROM working_memory WHERE id IN (${placeholders}) AND consolidated_at = ?`).all(...ids, claimTs)).map(...));
if (claimed.size === 0) return { dry_run: false, status: "no_op", message: "All eligible rows claimed by concurrent sleep" };
rows = rows.filter(row => claimed.has(rowValue(row, "id")));
```

**Flow:** eligible old working rows (TTL/2 cutoff, `consolidated_at IS NULL`) are CLAIMED by timestamped `consolidated_at` write, then ownership is re-read — only rows still bearing this run's claim survive (concurrent-sleep safety) → group by source → chunk via `splitSleepItems` → `buildSleepSummary` per chunk (truncation metadata recorded honestly) → `consolidateToEpisodic` inserts one episodic row carrying `summary_of` = joined source ids, widest scope wins (`global` beats `session`), tightest `valid_until` wins, veracity clamped, then extracts facts, ingests the episodic graph, schedules embeddings, emits `MEMORY_CONSOLIDATED` → `sleepAllSessions` iterates sessions via scoped beam clones and finishes with `degradeEpisodic`. DRIFT NOTE: the legacy v1 capsule's pairwise same-fact merge loop (`merge neighbors below similarity threshold`) no longer exists at HEAD — consolidation is summarize-to-episodic plus degradation.

**Invariant:** a working-memory row is consumed exactly once even under concurrent sleepers (claim-and-verify); episodic summaries always keep provenance (`summary_of`) so recall can dedupe cross-tier links.

**Probe:** `test/beam-consolidate-unit.test.ts`; concurrency pins in `test/consolidate-fact-concurrency.test.ts`, `-fact-id-collision.test.ts`, `-fact-sibling-races.test.ts` (claim atomicity).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", name_pattern: "^(recall|recallEnhanced|sleep|sleepAllSessions|consolidateToEpisodic|clipRecallContent|scoreCandidate)$", limit: 16, fields: ["signature"] });
await mcp.codebase_memory.get_code_snippet({ project: "oh-my-pi", qualified_name: "oh-my-pi.packages.mnemopi.src.core.beam.recall.recall" });
```

## Verdict
Adopt fused multi-signal scoring with tier-specific blends, veracity weights, honest clipped previews, and claim-then-verify consolidation; adapt weights/thresholds/TTL and the summary builder to host; omit the LLM-summary path and language detection until a target needs them.
