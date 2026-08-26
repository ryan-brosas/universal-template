<!-- capsule-v2 -->
# Sent-view arbitration — which token number drives compression decisions, and why the host's "real usage" can be a false emergency?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** Your host reports a context-usage number — should nudge/emergency decisions trust it? What is the contract for computing the decision-scale token count?

## The host's real usage has two regimes; only one is decision-safe
**Path/Symbol:** `src/index.ts`:186-210 (`realUsage` capture, sent-view assembly, calibration, armed-emergency boost); `src/tokens.ts`: `estimateTokens` (:12-18, skips `toolName === "compress"` messages and covered ids over chars/4), `calibrateTokens` (:27-29); shared-panel twin `src/commands.ts`:115-152 (`statusReport` — same arithmetic for the human view); `src/footer-status.ts` whole (51L).
**Signature:** `sentTokens = estimateTokens(coreMessages, coveredIds) + systemPromptTokens`; `tokenCount = calibrateTokens(sentTokens, density.densityFor(modelId))`.
**Data Shape:** three scales coexist and must never mix: (a) SENT VIEW = chars/4 over the pruned projection + measured system prompt; (b) TREE SCALE = host summing the whole session tree including originals; (c) PROVIDER USAGE = last assistant's reported totals.
### Decisive source
```ts
// index.ts:175-185 — the false-emergency narrative that justifies the whole seam:
// pi's getContextUsage is anchored on the last assistant's provider-reported
// usage when available (≈ sent view, fine), but it falls back to summing the
// whole session tree (originals included, never shrinks) when providers report
// no usage. After compression ... that tree number can exceed the window many
// times over while the real sent view is a few percent — permanent false
// EMERGENCY nudges while the session keeps working (issue #18 report; same
// omp 180K-window / 366K-tree class). The tree-scale number stays in logs only.
const realUsage = ctx.getContextUsage?.();
const sentTokens = estimateTokens(coreMessages, coveredIds) + systemPromptTokens;
let tokenCount = calibrateTokens(sentTokens, runtime.density.densityFor(modelId));
```
**Flow:** every processTurn site (context transform AND statusReport) now arbitrates on the CALIBRATED sent view: raw chars/4 estimate over uncovered live messages + measured system prompt tokens, scaled by the learned per-model density. The tree-scale number (`realUsage?.tokens`) is demoted to log/diagnostics only. The armed overflow emergency then floors tokenCount at 95% of the window. The footer widget (`updateFooterStatus`, 500ms tick) renders delegate usage separately with pi-mirroring compact formatting (`formatCompactTokens`: lowercase k/M thresholds <1000/<10000/<1e6/<1e7) and no-ops when text is unchanged; teardown wraps `setStatus(undefined)` in try/catch ("session is tearing down — best effort").
**Invariant:** (1) This REPLACES the pass-2-era rule "prefer realUsage.tokens when positive" — that preference IS the bug when providers don't report usage (tree fallback). Porters reading older forks must not reinstate it. (2) System prompt must be MEASURED per turn via `getSystemPromptText(ctx)` + defaultCountTokens, not estimated — it rides outside coreMessages so it would otherwise be invisible to the sent view. (3) estimateTokens' two exclusions (compress-tool results, covered ids) are what make the sent view match what the provider actually receives post-pruning. (4) Panel/status views must derive Session-only numbers on the SAME estimation scale as the decisions — "never cross-scale" (commands.ts :137-141 comment re omp issue #18). (5) Footer updates must be idempotent no-ops on unchanged text because they run on a timer.
**Probe:** `cd /mnt/hdd/utopia/inspo/coding-agents/billion-context-pi && npx tsx --test tests/sent-view-arbitration.test.ts tests/footer-status.test.ts tests/tokens.test.ts` — GREEN at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "estimateTokens calibrateTokens getContextUsage sent view statusReport", limit: 10 });
```

## Verdict
Adopt the calibrated sent-view as THE decision scale, keep host usage numbers out of decision paths unless anchored on provider reports, measure the system prompt explicitly, and mirror the same scale into human-facing panels. Adapt the usage-source API and compact-number format to your host. Omit nothing from the exclusion set in estimateTokens — each exclusion corresponds to content the transform removes before sending.
