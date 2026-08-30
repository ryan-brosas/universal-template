<!-- capsule-v2 -->
# Payload mutation pipeline — how do you apply every vendor-specific payload adaptation in one ordered, testable, in-place step list?

**Source:** pi-provider-kimi-code MIT `main@794330400343d6f0cd0059635187b233c4d90273`; Codebase Memory `pi-provider-kimi-code`. **Question:** A porter adding vendor constraints (role renames, cache keys, thinking modes, tool-choice limits) to a generic provider payload must decide where each mutation lives and in what order it runs.

## Payload mutation pipeline
**Path/Symbol:** `src/payload.ts:471-646` (`applyKimiPayloadMutations`); sole caller `src/stream.ts` `onPayload` closure (confirmed by trace_path: callers_total=1).
**Signature:** `(payload: JsonRecord, ctx: KimiPayloadContext) => Promise<void>`; `KimiPayloadContext = { api: "anthropic-messages" | "openai-completions"; upload?: Uploader; uploadCacheScope?: string; cacheKey?: string; cacheRetention: CacheRetention; reasoning?: ThinkingLevel; modelConfig: KimiResolvedModelConfig }`.
**Data Shape:** Mutates the provider request payload JSON in place and returns void. Every side-effect source is pre-extracted into ctx: no process.env, fs, or network access inside the function itself ("pure given its context", payload.ts header comment 462-469).

### Decisive source
```ts
// 5. Spread extra_body into the top-level payload before normalization and
//    config caps. Top-level fields retain precedence over extra_body.
if (isRecord(payload.extra_body)) {
  const extraBody = payload.extra_body as JsonRecord;
  delete payload.extra_body;
  for (const [key, value] of Object.entries(extraBody)) {
    if (payload[key] === undefined) {
      payload[key] = value;
    }
  }
}
```
```ts
if (payload.tool_choice !== undefined) {
  const tc = payload.tool_choice;
  const isAllowed =
    tc === "auto" ||
    tc === "none" ||
    (isRecord(tc) && (tc.type === "auto" || tc.type === "none"));
  if (!isAllowed) {
    payload.tool_choice = isRecord(tc) ? { type: "auto" } : "auto";
  }
}
```

**Flow:** (1) map `role:"developer"` → `"system"` → (2) protocol-dispatched file-upload transform when ctx.upload present → OpenAI normalizers (drop empty assistant content beside tool_calls; back-fill tool parameter types) → `optimizeToolSchemas` on every payload.tools → (3) inject `prompt_cache_key` unless retention is `"none"` or caller set one → (4) `stream_options.include_usage` for streaming OpenAI only → (5) spread extra_body with top-level precedence → (6) `max_tokens`→`max_completion_tokens` rename + generation caps (temperature/top_p deleted unless explicitly configured; maxTokens clamped via Math.min) → (7) delete top-level reasoning_effort, resolve thinking level through the model's supportsThinkingType ladder (`no` → delete thinking; `only` → force low/enabled; adaptive shape keeps effort in `output_config`) and restore empty `reasoning_content:""` on replayed assistant turns when keep==="all" → (8) downgrade disallowed tool_choice to auto LAST because it depends on the final thinking mode.
**Invariant:** Step order is load-bearing: extra_body must precede caps so config wins over extras; thinking resolution must precede tool_choice downgrade (server rejects required/function tool_choice while thinking is always-on); a mutation that needs another's output must run after it. The function never reads ambient state, so identical ctx+payload ⇒ identical result.

**Probe:** `tests/payload.test.ts` — line 37 pins developer→system; 50-89 pin prompt_cache_key inject/none/existing-key precedence; 391-426 pin temperature/top_p omission and tool_choice clamp; 485-546 pin adaptive output_config mapping; 608+ pin max_tokens rename/caps.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-provider-kimi-code", query: "applyKimiPayloadMutations payload mutations", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the single-entry in-place pipeline with an effect-free context object and numbered, order-documented steps — it ports to any vendor adapter. Adapt the concrete steps, field names, and env-derived defaults to your endpoint's constraint list. Omit Moonshot specifics (prompt_cache_key semantics, thinking/output_config shapes, ms:// uploads) unless the target API shares them. Coverage caveat: none — all cited paths are fully indexed at this pin.
