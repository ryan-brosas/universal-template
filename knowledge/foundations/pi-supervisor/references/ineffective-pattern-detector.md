<!-- capsule-v2 -->
# Ineffective-pattern detector — timestamp-based similarity over the last 3 interventions plus a 60s stagnation arm

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you detect that steering is not working using only the intervention ledger, with no turn counting?

## Two detection arms
**Path/Symbol:** `src/state/patterns.ts:22-52` (`detectIneffectivePattern`), similarity kernel :54-82 (`areMessagesSimilar`).
**Signature:** `detectIneffectivePattern(state: Pick<SupervisorState,'interventions'|'startedAt'>): { detected: boolean; similarCount: number; secondsSinceLastSteer: number }`.
**Data Shape:** Reads only interventions + startedAt; `STAGNATION_SECS = 60`; recent window = last 3 messages.

### Decisive source
```ts
  const lastSteerTs =
    state.interventions.length > 0
      ? state.interventions[state.interventions.length - 1].timestamp
      : state.startedAt;
  const secondsSinceLastSteer = Math.round((now - lastSteerTs) / 1000);
  const stagnating = secondsSinceLastSteer >= STAGNATION_SECS;

  const recent = state.interventions.slice(-3);
  ...
  const messages = recent.map((iv) => iv.message.toLowerCase());
  let similarCount = 1;
  for (let i = 1; i < messages.length; i++) {
    if (areMessagesSimilar(messages[i - 1], messages[i])) similarCount++;
  }
  const detected = similarCount >= 2 || stagnating;
```
Similarity kernel (:59-79): exact match after punctuation-strip ⇒ similar; ELSE shared directive words (`focus implement add fix create build need should must`) ≥ 2 ⇒ similar; ELSE length-ratio > 0.7 AND ≥ 1 shared directive ⇒ similar.

**Flow:** at each settled check → compute staleness from last timestamp → pairwise-similarity walk over last 3 steer messages → detected = repetition OR stagnation → feeds reframe-tier escalation and the prompt's INEFFECTIVE-PATTERN warning.
**Invariant:** Timestamps replace turn counts entirely (works across restarts and compaction since timestamps live in persisted interventions). Stagnation uses startedAt as the baseline when NO intervention exists yet, so a silent supervisor still ages into stagnation. similarCount starts at 1 and needs only one adjacent similar pair (≥2) to trip — cheap and deliberately sensitive.
**Probe:** `grep -c "STAGNATION_SECS = 60" src/state/patterns.ts` → 1; `grep -c "commonDirectives.length >= 2\|lenRatio > 0.7" src/state/patterns.ts` → 2; `grep -cF "slice(-3)" src/state/patterns.ts` → 1. Direct tests: `tests/state.test.ts:102` describe('ineffective pattern detection').

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "detectIneffectivePattern|escalateReframeTier", limit: 10 });
```

## Verdict
Adopt ledger+timestamp ineffectiveness detection as the trigger for strategy escalation; adapt the directive-word list and similarity thresholds to your steering vocabulary. Omit embeddings/LLM similarity — the point is a free deterministic detector that can run every turn.
