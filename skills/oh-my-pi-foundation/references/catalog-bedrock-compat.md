<!-- capsule-v2 -->
# Bedrock per-model cache + watchdog compat — why does every Claude generation need its own checkpoint floor?

**Source:** Oh My Pi MIT `main@96f428097`; Codebase Memory `oh-my-pi`. **Question:** How do you encode AWS's per-model prompt-cache limits and pingless-stream watchdog floors?

## Model-card-sourced checkpoint table + reasoning-tiered idle timeouts
**Path/Symbol:** `packages/catalog/src/compat/bedrock.ts:EXPLICIT_CHECKPOINTS_*` (:15–56), `detectedBedrockCompat` (:61), `BEDROCK_REASONING_STREAM_IDLE_TIMEOUT_MS` (:131), `BEDROCK_ADAPTIVE_THINKING_STREAM_IDLE_TIMEOUT_MS` (:141), `buildBedrockCompat` (:146).
**Signature:** `buildBedrockCompat(spec): ResolvedBedrockCompat {promptCacheMode, supportsLongPromptCacheRetention, promptCacheMinimumTokens, promptCacheMaximumCheckpoints, streamIdleTimeoutMs}`.
**Data Shape:** six preset records (1024/2048/4096/512 min-tokens × 5m/1h retention, max 4 checkpoints); Nova family pinned by EXACT id list incl. cross-region prefixes (us./eu./jp./global.).

### Decisive source
```ts
// This list is deliberately sourced from AWS MODEL CARDS, not cache pricing:
// keep exact documented model/inference-profile IDs conservative rather than
// treating arbitrary Nova-like application profiles as checkpoint-capable.
// Opus 5: 512-token minimum per its model card — the ONLY 512 preset.
if (id.includes("anthropic.claude-opus-5")) return EXPLICIT_CHECKPOINTS_512_1H;

// Bedrock ConverseStream sends NO ping/keepalive events: a reasoning model
// quiet mid-thinking reads as a dead stream at the generic 300s floor (#4758).
const BEDROCK_REASONING_STREAM_IDLE_TIMEOUT_MS = 600_000;
// Adaptive-thinking families run longest quiet gaps (display default
// "omitted" since Opus 4.7 / Fable 5); direct Anthropic tolerates 3x the
// idle budget thanks to pings (#4900) — pingless Bedrock needs 900s raw.
const BEDROCK_ADAPTIVE_THINKING_STREAM_IDLE_TIMEOUT_MS = 900_000;
```

**Flow:** lowercased model id → exact/prefix table walk (Nova exact ids → Claude generations by `includes`) → checkpoint preset copied (never share the frozen record) → stream floor layered by `spec.reasoning` + adaptive-display identity predicate → sparse overrides applied.
**Invariant:** (1) checkpoint capability is allowlisted per documented profile — inference-profile lookalikes stay cache-less; (2) minimum-token floors differ PER GENERATION (512→1024→2048→4096); (3) watchdog widening is keyed on reasoning AND adaptive-generation, not a blanket value; (4) explicit spec overrides always win.
**Probe:** direct `packages/catalog/test/amazon-bedrock-openai.test.ts:37` (routing suite); checkpoint table itself has no dedicated unit file — coverage caveat recorded; contract anchored to cited AWS model-card URLs in comments.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "detectedBedrockCompat promptCacheMinimumCheckpoints bedrock streamIdleTimeout", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the preset-record pattern with copy-not-mutate and the reasoning-tiered idle ladder; re-derive the checkpoint table from AWS docs when you port (it drifts with each release); omit Nova entries if unsupported. Coverage caveat: table verified against cited model cards, not unit tests.
