<!-- capsule-v2 -->
# Thinking metadata derivation — how do you compute a model's effort ladder once, then never parse ids per request?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** Where does the supported thinking-effort set come from, and how do explicit config, wire truth, and stale caches interact?

## Build-once derivation + field-read runtime helpers (hard architectural split)
**Path/Symbol:** `packages/catalog/src/model-thinking.ts:resolveModelThinking` (:145), `fillThinkingWireDefaults` (:170), `getModelDefinedEfforts` (:321), `impliesMandatoryReasoning` (:611), `inferThinkingControlMode` (:679), `clampThinkingLevelForModel` (:774), `resolveWireModelId` (:871), `minimumSupportedEffort` (:879); `effort.ts:Effort/THINKING_EFFORTS`.
**Signature:** `resolveModelThinking(spec, compat): ThinkingConfig | undefined`; `clampThinkingLevelForModel(model, requested): Effort | undefined`; `resolveWireModelId(model, effort|undefined): string`.
**Data Shape:** `ThinkingConfig {mode: budget|effort|google-level|anthropic-adaptive|anthropic-budget-effort, efforts: Effort[], effortMap?, defaultLevel?, requiresEffort?, supportsDisplay?, suppressWhenOff?, effortRouting?}` — six canonical efforts `minimal..max`.

### Decisive source
```ts
// Derivation runs EXACTLY once per model; everything below the "runtime
// helpers" divider reads baked fields only — no id parsing, no host
// matching, no compat detection per request.
if (!spec.reasoning) return undefined;
// "reasoning: true, thinking: undefined" IS the encoding for
// "thinks, but exposes no control surface".
if (omitsWireReasoningEffort(spec.api, compat)) return undefined;
// Devin cascade selects effort by ROUTING to sibling ids; never fabricate
// an identity-derived ladder for it.
if ((compat as ResolvedDevinCompat)?.trustExplicitThinkingOnly === true) return undefined;

// Stale cached ladders are re-normalized on every build when the model-
// defined (wire-truth) ladder disagrees:
const normalizedEfforts = getModelDefinedEfforts(spec, compat) ?? thinking.efforts;
```

**Flow:** `buildModel` calls `resolveModelThinking` after compat → explicit spec thinking owns mode/efforts but gets wire facts (`effortMap`, `supportsDisplay`, `requiresEffort`, `defaultLevel`) backfilled from identity → sparse specs infer fully (`getModelDefinedEfforts` host-specific GLM-5.2 dialects → Kimi K3 / DeepSeek V4 wire-exact low/high/max → GPT-5.6+ five-tier → Anthropic adaptive 5-tier vs 4-tier by real-xhigh generation → Qwen template low/medium/xhigh → Ollama low..max → family fallbacks) → empty result throws (never ship a reasoner with no dial) → runtime helpers clamp requests DOWN to the nearest supported level or floor to `levels[0]`.
**Invariant:** (1) mandatory-reasoning families (Gemini 3+, o-series, MiniMax M2, GLM-5.3+, `*-thinking` orphan SKUs) have no off state — thinking-off requests clamp to the LOWEST effort via `minimumSupportedEffort`; (2) collapsed pairs drop `requiresEffort` because the pair CAN turn off (routes to bare backing id) even though the thinking member alone cannot; (3) Google `MINIMAL` must map to `LOW` when collapse routes minimal and low onto the same `-low` wire id (CCA rejects MINIMAL there); (4) explicit `false` overrides always win over inference except the stale-cache re-derive case.
**Probe:** direct `packages/catalog/test/model-thinking.test.ts:39` (derivation incl. per-host GLM dialects), `:784` (clamp from explicit metadata, non-reasoning off, xhigh hidden on binary-thinking transports, Z.AI high/max pair), `:1010` (Qwen 3.8 local template ladder).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveModelThinking ThinkingConfig efforts requiresEffort", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the derive-once/read-fields split, the stale-ladder re-normalization, and the mandatory-reasoning floor; adapt the per-host effort tables (wire truth changes vendor-side); omit google-level/anthropic-adaptive modes if you don't speak those APIs. Coverage caveat: none — 1,092-line direct test file.
