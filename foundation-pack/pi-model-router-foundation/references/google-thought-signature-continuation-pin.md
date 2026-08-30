<!-- capsule-v2 -->
# Google thought-signature continuation pin — why must a mid-task tool-result continuation keep the same Google model?

**Source:** pi-model-router MIT `main@002b48f9bb03c068e0ef97eb230f49df57a24f93`; Codebase Memory `pi-model-router`. **Question:** When a router switches tiers between a tool call and its tool-result turn, how do I avoid provider-side replay errors on signed thinking blocks?

## Previous-decision preservation guard
**Path/Symbol:** `extensions/provider.ts:streamSimple` (lines 320–344), executed after heuristics/classifier produced a fresh decision but before any delegation.
**Signature:** predicate over `(lastMessage, previousDecision, decision)`.
**Data Shape:** Requires the last message to be role `'toolResult'`; compares `previousDecision` vs fresh `decision` on provider (`=== 'google'`), thinking (`!== 'off'` on both), and target label (must DIFFER).

### Decisive source
```ts
const isGoogleThinkingToolContinuation =
  lastMessage?.role === 'toolResult' &&
  previousDecision?.profile === model.id &&
  previousDecision.targetProvider === 'google' &&
  previousDecision.thinking !== 'off' &&
  decision.targetProvider === 'google' &&
  decision.thinking !== 'off' &&
  previousDecision.targetLabel !== decision.targetLabel;

if (isGoogleThinkingToolContinuation && previousDecision) {
  decision = {
    ...decision,
    tier: previousDecision.tier,
    phase: previousDecision.phase,
    targetProvider: previousDecision.targetProvider,
    targetModelId: previousDecision.targetModelId,
    targetLabel: previousDecision.targetLabel,
    thinking: previousDecision.thinking,
    reasoning:
      `Preserved ${previousDecision.targetLabel} for a Google tool-result continuation ` +
      `to avoid thought-signature replay errors. (Original: ${decision.reasoning})`,
  };
}
```

**Flow:** fresh decision computed normally → guard evaluates → if pinned, ALL routing fields are replaced by the previous turn's values while the original reasoning is preserved as a parenthetical suffix — the audit trail keeps both what would have happened and why it was overridden. The very next block (`state.lastDecision = decision`) persists the pinned decision, so the pin also becomes the baseline for the following turn.
**Invariant:** Never send a Google request whose history contains thinking blocks signed by a different Google model mid-continuation; scope the pin narrowly (toolResult boundary + google + thinking + label change) so every other transition still re-routes freely.
**Probe:** `extensions/provider.test.ts` :229–300 — seeds `lastDecision` as `google/gemini-2.5-pro` (thinking high), makes high tier resolve to a different google model via toolResult context, asserts final `targetModelId === 'gemini-2.5-pro'` and reasoning contains `'Preserved google/gemini-2.5-pro for a Google tool-result continuation'`.

## Get live surrounding code
**Retrieve (executed live at pin):**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-model-router", query: "streamSimple routing decision override", limit: 5 });
// → rank-1 pi-model-router.extensions.provider.streamSimple (provider.ts:249-607), which contains this guard.
```
Retrieval caveat: the naive form `"google thinking toolResult continuation preserve"` MISSES — it surfaces
thinking-level helpers (`getThinkingOverride`, `handleThinking`, `clampThinkingLevel`) because the guard is an
inline local inside `streamSimple`, not a graph node. Land on `streamSimple` first, then read :320–344.

## Verdict
Adopt the narrow five-condition guard and full-field preservation with reasoning-suffix audit exactly; adapt the provider test (`'google'`) to whichever of your providers signs thinking content; omit nothing from the guard — loosening any single condition reintroduces the replay failure this seam exists to prevent.
