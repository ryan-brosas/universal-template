<!-- capsule-v2 -->
# Compaction trigger budget — when does a transcript actually compact?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `ext-cline`. **Question:** How does the runtime decide "this request exceeds the context window" from token *estimates*, and what exactly is measured?

## Trigger gate over request-level estimate
**Path/Symbol:** `sdk/packages/core/src/extensions/context/compaction.ts:296-323` (`createContextCompactionPrepareTurn`) + `compaction-shared.ts:51-70` (`resolveEffectiveMaxInputTokens`).
**Signature:** `shouldCompact = requestInputTokens >= maxInputTokens * COMPACTION_TRIGGER_RATIO`.
**Data Shape:** `requestInputTokens = estimateRequestInputTokens({systemPrompt, messages: apiMessages, tools})` — system prompt AND tool schemas count toward the trigger, not just chat history. `apiMessageTokens` sums per-message estimates; `requestOverheadTokens = max(0, requestInputTokens - apiMessageTokens)` is the non-message share (system prompt + tools).

### Decisive source
```ts
export const DEFAULT_MAX_INPUT_TOKENS = 128_000;
export const CONTEXT_WINDOW_INPUT_RATIO = 0.9;
export const COMPACTION_TRIGGER_RATIO = 0.9;

// resolveEffectiveMaxInputTokens:
if (maxInputTokens !== undefined) {
    return contextWindow === undefined
        ? maxInputTokens
        : Math.min(maxInputTokens, contextWindow);
}
return contextWindow === undefined ? undefined : contextWindow * CONTEXT_WINDOW_INPUT_RATIO;
```

**Flow:** model metadata → effective input limit (`maxInputTokens` authoritative but capped at context window; context-window-only models get 90% of the window as usable input) → `requestTriggerTokens = limit × 0.9` → compare full-request estimate against it each turn. Auto mode returns early (`undefined`) without compacting below the trigger. Effective 81%-of-window compaction point for window-only models (0.9×0.9).
**Invariant:** The trigger compares REQUEST-level estimates (including overhead), never raw message totals; a porter who triggers on message tokens alone fires too late for tool-heavy sessions where schemas dominate.
**Probe:** `grep -cF 'CONTEXT_WINDOW_INPUT_RATIO = 0.9' sdk/packages/core/src/extensions/context/compaction-shared.ts` → 1; `grep -cF 'shouldCompact = requestInputTokens >= requestTriggerTokens' .../compaction.ts` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cline", query: "resolveEffectiveMaxInputTokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-rung budget ladder (explicit maxInputTokens ∩ contextWindow → contextWindow×0.9 → default 128k) and request-level triggering with separate message/overhead accounting; adapt ratios to host policy; omit Cline's telemetry capture fields around the gate. Direct tests exist upstream (compaction.test.ts pins 90%/81% triggers) but were not runnable here (no node_modules in clone); deterministic greps executed instead.
