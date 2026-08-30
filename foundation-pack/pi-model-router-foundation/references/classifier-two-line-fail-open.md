<!-- capsule-v2 -->
# Classifier two-line fail-open protocol — how does the optional LLM classifier override stay cheap and never break routing?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** How do I add an LLM-based tier classifier that can upgrade heuristic decisions yet degrades to pure heuristics on every failure mode?

## Fail-open streaming classifier
**Path/Symbol:** `extensions/routing.ts:runClassifier` (lines 389–476); invocation gate `extensions/provider.ts:streamSimple` (lines 294–318).
**Signature:** `runClassifier(classifierModelRef, modelRegistry, context, currentPhase?, thinking?): Promise<{ tier: RouterTier; reasoning: string } | undefined>`.
**Data Shape:** Classifier is configured as `{ model: "provider/id", thinking?: ThinkingLevel }`. The prompt embeds tier definitions, the current phase (with phase-specific bias sentences), the last 4 conversation messages, and demands exactly two output lines.

### Decisive source
```ts
const lines = fullText.trim().split('\n');
const tierLine = lines.find((l) => l.toLowerCase().startsWith('tier:'));
const reasoningLine = lines.find((l) => l.toLowerCase().startsWith('reasoning:'));
if (tierLine) {
  const tierValue = tierLine.split(':')[1].trim().toLowerCase();
  if (isRouterTier(tierValue)) {
    return { tier: tierValue,
             reasoning: reasoningLine ? reasoningLine.split(':')[1].trim() : 'Classifier decision.' };
  }
}
} catch { /* Ignore classifier errors and fall back to heuristics */ }
return undefined;
```
**Flow:** parse canonical ref → registry lookup (`undefined` if absent) → `getApiKeyAndHeaders` (`undefined` unless ok AND apiKey present) → build single-user-message Context → stream via the same `streamSimple`, accumulating only `text_delta` strings → line-scan/validate → on success the provider REBUILDS the whole decision via `buildRoutingDecision(..., \`Classifier: ${reasoning}\`, ..., true)`, overwriting the heuristic one; on ANY failure return `undefined` and keep heuristics.
**Invariant:** The classifier is advisory-only and strictly cheaper than a wrong turn: it is skipped for pinned tiers, rule wins, and budget-exceeded sessions (the downgrade is inevitable, so the call would be wasted). Reasoning mode reaches the classifier model only when `model.reasoning && thinking && thinking !== 'off'`. `isClassifier: true` marks rebuilt decisions.
**Probe:** `extensions/routing.test.ts` :532–550 (streamed `'Tier: high\n'` + `'Reasoning: ...'` deltas parse to `{ tier: 'high', reasoning }`), :552–564 (invalid format ⇒ `undefined`). Caveat: no upstream test covers the provider skip gate or the mid-stream error path — source-pinned at :292–299/:476.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "runClassifier Tier reasoning two lines", limit: 10 });
```

## Verdict
Adopt: fixed-format two-line wire contract, line-prefix parsing from accumulated deltas, typed tier validation before acceptance, and undefined-means-fail-open. Adapt the prompt's tier definitions/bias sentences to your ladder. Omit the pi-ai stream plumbing in favor of your host's completion API — but keep the "no throw escapes runClassifier" wrapper, which is the entire reliability story.
