<!-- capsule-v2 -->
# Model-keyed compaction thresholds — how do you defer a host's automatic compaction until the ACTIVE model's own configured threshold is crossed?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how are per-model token/ratio compaction thresholds keyed, evaluated, and enforced against Pi's built-in auto-compaction — and which wins when both are configured?

## provider/model key ladder: token beats ratio; hook cancels premature host compaction
**Path/Symbol:** `src/compaction/threshold.ts` whole (:1-56): `modelCompactionKey` (:4-6), `configuredCompactionTokenThreshold` (:11-15), `configuredCompactionThreshold` (:17-21), `runThresholdCompact` (:23-35), `compactAtConfiguredThreshold` (:37-56). Enforcement twin in `src/compaction/hook.ts` session_before_compact handler (:819-845) using `getThresholdTokens`/`getThresholdContextRatio` options (:803-809). Call site: `src/index.ts:382` inside the agent_settled handler. Direct tests `tests/compaction-threshold.test.ts` (125 lines).
**Signature:** `modelCompactionKey(model?: {provider,id}): string | undefined` → `` `${provider}/${id}` ``; `compactAtConfiguredThreshold(context, config): Promise<boolean>` (true = compacted).
**Data Shape:** `config.compaction.tokenThresholds: Record<modelKey, number>` (absolute tokens), `config.compaction.thresholds: Record<modelKey, number>` (context ratio 0..1); usage `{tokens: number|null, contextWindow, percent: number|null}`.

### Decisive source
```ts
// threshold.ts :37-56
const modelKey = modelCompactionKey(context.model);
const usage = context.getContextUsage();
if (usage === undefined) return false;
const tokenThreshold = configuredCompactionTokenThreshold(config, modelKey);
if (tokenThreshold !== undefined) {
  if (usage.tokens === null || usage.tokens < tokenThreshold) return false;
  return runThresholdCompact(context);          // resolve(true) on complete
}
const threshold = configuredCompactionThreshold(config, modelKey);
if (threshold === undefined || usage.percent === null) return false;
if (usage.percent / 100 < threshold) return false;
return runThresholdCompact(context);

// hook.ts :828-845 — DEFER Pi's earlier automatic compaction while below config
if (event.reason === "threshold"
    && typeof thresholdTokens === "number"
    && preparation.tokensBefore < thresholdTokens)
  return { cancel: true };
// ratio arm mirrors this with preparation.tokensBefore / contextWindow < threshold
```

**Flow:** after each settled turn (`src/index.ts:382`) the extension checks the active model's thresholds itself and proactively compacts via callback-style `context.compact({onComplete, onError})` wrapped as a Promise (UI notify + `resolve(false)` on error, :23-35); meanwhile the session_before_compact hook lets Pi's OWN threshold fire only when the configured value is actually met — reason must be exactly `"threshold"` (`"overflow"` always passes through uncanceled) and unknown-token or missing-window cases never cancel. Token threshold takes precedence over ratio for the same key; settings keep the maps mutually exclusive and hand-written configs resolve to the explicit token value (:8-10 comment).
**Invariant:** the same `provider/id` key string gates BOTH the proactive path and the deferral path — a porter that keys them differently gets compaction storms or never-ending growth; `null` tokens (freshly-after-compaction state) means NO action, not zero.
**Probe:** `bash -c 'cd /mnt/hdd/utopia/inspo/pi-ecosystem/pi-fabric && grep -n "usage.percent / 100 < threshold" src/compaction/threshold.ts'` → line 53; `grep -c "return { cancel: true }" src/compaction/hook.ts` → 5; tests: token-beats-ratio `expect(context.compact).not.toHaveBeenCalled()` :75, unknown-token skip :77-79, overflow passthrough :55-56/:109-110, unconfigured model no-op :121-123, `expect(invocation…)` style pin of proactive call `grep -c "await compactAtConfiguredThreshold(context, state.config)" src/index.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "compactAtConfiguredThreshold token threshold ratio model compaction", limit: 10, fields: ["signature", "name", "file"] });
```
(Rank #1 resolves `compactAtConfiguredThreshold` src/compaction/threshold.ts 37-56.)

## Verdict
Adopt the single canonical modelKey + token-over-ratio precedence + cancel-to-defer hook pattern for any host that owns an automatic compactor you want to re-threshold per model; adapt budgets/keys to your config schema; omit the proactive settled-turn trigger if your host compacts synchronously. Every branch direct-tested — no coverage caveat.
