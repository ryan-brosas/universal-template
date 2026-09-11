<!-- capsule-v2 -->
# ASI memory loop — free-form Actionable Side Information carried on interventions and summarized back into prompts

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How does the supervisor remember its own observations across turns when each analysis gets a freshly compacted context?

## Free-form dict on every steer
**Path/Symbol:** `src/types.ts:17-19` (`InterventionASI { [key: string]: unknown }`, carried in `SupervisorIntervention.asi?`); summary builder `src/core/prompt-builder.ts:68-137` (`buildASISummary`); system-prompt contract `src/core/prompt-loader.ts:75-93` (CLOSING THE ASI LOOP section).
**Signature:** `buildASISummary(interventions: SupervisorIntervention[]): string` over the last 5 interventions.
**Data Shape:** asi values are arbitrary JSON; keys are model-chosen free text (e.g. `repeated_unverified_claim`, `watch_for`).

### Decisive source
```ts
  const keyFrequency: Record<string, number> = {};
  for (const iv of recent) {
    if (!iv.asi) continue;
    for (const key of Object.keys(iv.asi)) {
      keyFrequency[key] = (keyFrequency[key] || 0) + 1;
    }
  }
  for (const [key, count] of Object.entries(keyFrequency)) {
    if (count >= 2) patterns.push(`Pattern seen ${count}x: "${key}"`);
  }
```
Suspicious-value sweep (:88-113): all asi values lowercased, checked against `[unverified, contradict, suspicious, fake, skip, manipulat, cheat, gaming, short-circuit]` ⇒ appends "require explicit proof before accepting done"; verification-failure count ≥ 2 ⇒ "agent has pattern of unreliable reporting".

**Flow:** system prompt REQUIRES asi on every steer (free-form keys) → interventions persist asi with the state entry → next analysis summarizes: recurring keys (≥2 of last 5) + suspicious-value warnings + verification-failure counts → the deciding LLM reads its own past observations before judging "done".
**Invariant:** The memory is WRITE-BY-MODEL / READ-BY-CODE: the supervisor LLM invents keys, deterministic code aggregates them — no schema negotiation, yet recurring patterns surface mechanically. Intervention history display caps at last 5 with full JSON.stringify of asi values.
**Probe:** `grep -c "suspiciousIndicators" src/core/prompt-builder.ts` → 2; `grep -c "verificationFailures >= 2" src/core/prompt-builder.ts` → 1; `grep -cF "count >= 2" src/core/prompt-builder.ts` → 1. Direct tests: `tests/engine.test.ts:283/:309/:344/:379` ("includes ASI from previous interventions", "surfaces recurring ASI patterns in summary", "warns about verification failures in ASI summary", "detects suspicious keywords in ASI values"); `tests/parsing.test.ts:194/:220` parse ASI arms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", name_pattern: "buildUserPrompt|inferOutcome", query: "ASI", limit: 10 });
```

## Verdict
Adopt write-free/read-aggregated side-channel memory for any recurring LLM judge: it survives context resets at zero storage cost. Adapt the suspicious-indicator list to your domain's cheating vocabulary. Omit fixed schemas — constraining keys would break the self-documenting loop the built-in prompt teaches.
