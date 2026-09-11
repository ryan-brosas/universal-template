<!-- capsule-v2 -->
# Reframe tier escalation — what does the supervisor say differently when steering keeps failing?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How are escalation levels represented, capped, and injected into the prompt without the LLM ever seeing raw tier numbers as instructions to itself?

## Reframe tiers 0–4 (`src/core/reframe.ts` + `src/state/reframe.ts`)
**Path/Symbol:** `src/core/reframe.ts:getReframeGuidance` (:6-27); `src/state/reframe.ts:escalateReframeTier` (:15-22), `MAX_TIER=4` (:7).
**Signature:** `getReframeGuidance(tier: number, ineffectivePattern?: IneffectivePattern): string`; `escalateReframeTier(state): boolean` (true = persisted change).
**Data Shape:** `ReframeTier = 0|1|2|3|4`; guidance is a plain string appended inside the user prompt between agent-status and context blocks.

### Decisive source
```ts
if (!ineffectivePattern?.detected && tier === 0) return '';   // silent by default
const tierGuidance = {
  1: 'REFRAME TIER 1 — DIRECTIVE: ...extremely specific about the next single action',
  2: 'REFRAME TIER 2 — SUBGOAL: ...smaller, verifiable milestone... just that one piece',
  3: 'REFRAME TIER 3 — PIVOT: ...completely different strategy... Challenge any assumptions',
  4: 'REFRAME TIER 4 — MINIMAL SLICE: ...smallest working version you can deliver right now',
};
const patternNote = detected ? `\n⚠ INEFFECTIVE PATTERN DETECTED: Last ${similarCount} steering
  messages were similar or no progress in (${secondsSinceLastSteer}s since last steer).` : '';
return tierGuidance[tier] + patternNote;
```

**Flow:** detection fires → `escalateReframeTier()` (no-op returning false at MAX_TIER=4, so escalation at the cap does NOT persist or re-append) → next `buildUserPrompt` embeds tier text + pattern note → supervisor's steer message changes STRATEGY (directive→subgoal→pivot→minimal slice) rather than repeating louder. Tier resets on `done`, `stop`, and fresh supervision start.
**Invariant:** (1) Escalation is monotone upward with a hard cap; only success/stop resets. (2) Tier-0 + no pattern ⇒ empty string, so normal steering prompts carry zero reframe noise. (3) The pattern note can appear AT tier 0 when a pattern is detected (`getReframeGuidance(0, {detected:true,...})` is non-empty) — warning text and strategy text are independent.
**Probe:** `tests/engine.test.ts` — `returns empty string for tier 0 without ineffective pattern` (:106), `returns pattern warning even for tier 0 when ineffective pattern detected` (:111), tier texts :120/:127/:134/:141; `tests/state.test.ts` `escalates reframe tier up to max of 4` (:56).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "getReframeGuidance REFRAME TIER escalateReframeTier", limit: 8 });
```

## Verdict
Adopt the 5-tier vocabulary (default/directive/subgoal/pivot/minimal-slice) + cap-and-reset algebra for any self-correcting prompt loop. Adapt wording; keep "strategy changes, not volume" semantics. Omit nothing — this file has no host coupling.
