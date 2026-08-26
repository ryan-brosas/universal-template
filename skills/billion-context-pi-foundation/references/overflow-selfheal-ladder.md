<!-- capsule-v2 -->
# Overflow self-heal ladder — how do you recover from a context-overflow 400 you failed to predict?

**Source:** billion-context-pi (MIT) `master@1c87eb5051e0e97bb6ba606dc1c57ec2510f1b41`; Codebase Memory project `mnt-hdd-utopia-inspo-coding-agents-billion-context-pi`. **Question:** When the model API rejects the request because the context is genuinely too large, what is the recovery contract — and what must a porter NOT do (rewrite/retry)?

## Detect → learn window → arm emergency → next turn re-centers
**Path/Symbol:** `src/overflow-selfheal.ts` whole (137L): `OVERFLOW_MARKER` (:33-34), `inspectOverflowMessage` (:46-50), `parseOverflowWindow` (:52-68), `toTokenNumber` (:70-74), `reserveOutputHeadroom` (:85-96), `shouldReserveOutputHeadroom` (:110-112), `OverflowEpisode` (:117-137); wiring `src/index.ts`:397-420 (`wireOverflowSelfHeal`) + :142-210 (context-event consumption).
**Signature:** `inspectOverflowMessage(haystack: string|undefined|null): { isOverflow, window?, message }`; `OverflowEpisode.learnedWindowFor(modelId): number | null`, `.armed: boolean`.
**Data Shape:** learned windows live in a per-session `Map<modelId, number>`; `armed` is session-scoped NOT per-model ("the context did not shrink, so the next turn needs the emergency regardless of which model answers it").
### Decisive source
```ts
// overflow-selfheal.ts:117-136 + index.ts:151-155 / :203-209 — the two halves
// of self-heal. Learn per MODEL (a bigger model mid-session must not inherit
// the smaller model's learned limit → premature compression), arm per SESSION:
if (info.window) ov.setLearnedWindow(modelId, info.window);
ov.armed = true;
// next context event:
let config = configBase;
const learnedWindow = ov.learnedWindowFor(modelId);
if (learnedWindow && learnedWindow > 0 && learnedWindow < config.modelContextLimit) {
  config = { ...config, modelContextLimit: learnedWindow };  // spread — never mutate shared config
}
...
if (ov.armed && config.modelContextLimit > 0) {
  ov.armed = false;
  const floor = Math.floor(config.modelContextLimit * 0.95);
  if (floor > tokenCount) tokenCount = floor;   // force kernel emergency band
}
```
**Flow:** `message_end` on assistant error messages builds the same haystack as throttle-retry (`errorMessage + "\n" + extractText(content)` — relays bury the upstream body in content); `OVERFLOW_MARKER.test` gates; four ordered window parsers extract the real limit (Anthropic `> N maximum`, OpenAI `maximum context length is N`, Responses `maximum context size is|of N`, generic `(maximum|limit) of N tokens`; comma-stripped, floor 1000 else rejected). The extension does NOT rewrite or retry this error — "the overflow is real, and re-sending the same context would overflow again. The error surfaces; the next turn recovers." Next turn re-centers bands below the real window (fallback 150k puts nudge/truncate bands ABOVE a smaller real window so nothing fires before the overflow), then arms ≥95% usage so emergency nudge + tool-result truncate fire immediately even if the density-calibrated estimate under-reports.
**Invariant:** (1) `OVERFLOW_MARKER` is deliberately a SUPERSET of throttle-retry's `OVERFLOW_GUARD` (:20-22 comment) and mirrors pi-ai's own patterns for providers whose text the shorter set missed — keep them in sync when either changes, or throttles get classified as overflows (or vice versa). (2) Learned-window re-centering only ever SHRINKS the limit (`learned < config` guard) and spreads into a new config object — never mutates the shared resolved config. (3) Output headroom reservation is API-family conditional: Anthropic enforces input independently of max_tokens so reserving would shift every band down for nothing; OpenAI-family counts output against the window; unknown APIs reserve conservatively (miss = one overflow, self-heal corrects). (4) `maxOutput >= window` requests are degenerate and left to self-heal rather than producing window ≤ 0.
**Probe:** `cd /mnt/hdd/utopia/inspo/coding-agents/billion-context-pi && npx tsx --test tests/overflow-selfheal.test.ts` — GREEN at pin (window parse per provider phrasing, marker superset vs Bedrock-throttle non-match, headroom reservation matrix).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-coding-agents-billion-context-pi", query: "OverflowEpisode inspectOverflowMessage reserveOutputHeadroom armed", limit: 10 });
```

## Verdict
Adopt the learn+arm ladder, per-model windows with session-scoped arming, the shrink-only re-center with spread-not-mutate, the API-family headroom rule, and the honest "do NOT retry an overflow" stance (contrast with throttle-retry's rewrite+kick). Adapt error-shape access and the provider phrase list to your providers — but keep the superset/sync relationship between any throttle classifier and this marker.
