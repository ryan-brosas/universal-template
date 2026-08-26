<!-- capsule-v2 -->
# Orchestrator failure ladder — when does a partially-failed scan count as success?

**Source:** Roo-Code Apache-2.0 `main@b867ec91`; Codebase Memory `Roo-Code`. **Question:** After a full scan with some batch errors, which exact predicate decides Error vs Indexed?

## Cumulative-counter failure classification
**Path/Symbol:** `src/services/code-index/orchestrator.ts:startIndexing` (:91-341; classification block :252-287).
**Signature:** `startIndexing(): Promise<void>` — internal counters `cumulativeBlocksIndexed`, `cumulativeBlocksFoundSoFar`, `batchErrors: Error[]`.
**Data Shape:** scanner callbacks feed the counters (`onFileParsed` grows found-so-far; `onBlocksIndexed` grows indexed). Classification runs AFTER the scan resolves, BEFORE `_startWatcher()`.

### Decisive source
```ts
if (cumulativeBlocksIndexed === 0 && cumulativeBlocksFoundSoFar > 0) { /* total failure */ }
const failureRate = (foundSoFar - indexed) / foundSoFar
if (batchErrors.length > 0 && failureRate > 0.1) { /* >10% lost = partial failure */ }
```

**Flow:** four rungs, first match throws into the catch handler: (1) zero indexed but >0 found WITH batch errors → "Indexing failed"; (2) same counts with NO errors recorded → critical-failure i18n message; (3) batchErrors present AND failureRate > 0.1 → partial-failure message naming counts; (4) otherwise SUCCESS — silent small losses (<10%) still reach `markIndexingComplete()` + state "Indexed".
**Invariant:** ≤10% block loss with errors is deliberately tolerated as success — a port that fails closed on ANY batch error turns flaky embedder blips into full collection wipes (the catch calls `clearCollection()` when `indexingStarted`). The abort path is checked FIRST (signal.aborted → Standby + cache flush, no error).
**Probe:** `src/services/code-index/__tests__/orchestrator.spec.ts`; deterministic pins executed: `failureRate > 0.1` at :268, zero-blocks rungs :256-287.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "CodeIndexOrchestrator startIndexing cumulativeBlocksIndexed batchErrors", limit: 10, fields: ["signature", "name", "file"] });
```
## Verdict
Adopt the counter-based ladder and its ordering (abort → total → rate → success), including the 0.1 threshold as a tunable constant. Adapt error-message i18n. Omit vscode workspace guards. Caveat: the incremental-scan branch (:140-205) reports progress but applies NO failure-rate gate — only the full-scan branch classifies failures.
