<!-- capsule-v2 -->
# Auto-model resolution + reasoning wire duality — how does one chat-completions stream serve model selection AND two reasoning dialects?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter exposing an "Auto" model over provider-compatible streams must pin exactly one concrete model per response and normalize provider-native reasoning fields without breaking strict SDK validation.

## streamChunks normalization pipeline
**Path/Symbol:** `agent-runtime/src/rpc-model-provider.ts:RpcChatCompletionsModelProvider.streamChunks` (:74-134), `normalizeReasoningContent` (:198-224), `restoreReasoningContent` (:261-271), `autoResponseModel` (:242-252), `concreteModel` (:232-240), `normalizeEmptyToolArguments` (:137-190).
**Signature:** `private async *streamChunks(request, signal?): AsyncIterable<JsonObject>`; pages arrive as `{streamId, chunks[], done, route?}` via the reserved host tool.
**Data Shape:** Latched state per provider instance: `resolvedModel?: string`, `reasoningWireFormat?: "reasoning"|"reasoning_content"`, `latestRoute?`.

### Decisive source
```ts
if (autoRequested && this.resolvedModel)
  request.model = `${RESOLVED_AUTO_MODEL_PREFIX}${encodeURIComponent(this.resolvedModel)}`;
// steering injected as trailing user messages at THIS boundary, then acked
for (const chunk of page.chunks) {
  const chunkModel = autoResponseModel(chunk.model);      // throws on non-string,
  if (chunkModel && this.resolvedModel && chunkModel !== this.resolvedModel)
    throw new Error("...conflicting selected models");     // two models = fatal
  if (chunkModel) this.resolvedModel = chunkModel;
  const n = normalizeReasoningContent(chunk);              // delta.reasoning_content → delta.reasoning
  if (n.wireFormat === "reasoning_content") this.reasoningWireFormat = "reasoning_content";
  else this.reasoningWireFormat ??= n.wireFormat;          // sticky latch
  yield normalizeEmptyToolArguments(n.chunk, toolArgumentState); // "" args → "{}" at finish_reason:"tool_calls"
}
if (page.done && autoRequested && !this.resolvedModel)
  throw new Error("...did not identify its selected model");
// restoreReasoningContent(request): on the NEXT request, assistant messages get
// reasoning_content restored from reasoning (deleted from reasoning) for GLM-style providers.
```

**Flow:** request rewrite (once resolved, later pages carry `__june_auto_resolved__:` so the HOST routes to the same concrete model) → steering injection → per-chunk: single-canonical-model enforcement → reasoning rename with sticky wire-format latch → empty-tool-args patch → yield. On continuation requests when the latch says `reasoning_content`, assistant history is rewritten back to the native field BEFORE sending.
**Invariant:** Exactly ONE canonical concrete model may appear across all chunks of one response (conflict / non-string / reserved `__june_*` tag / whitespace-or-control chars ⇒ throw — never guess); a done page without a resolved Auto model is fatal; the rename is lossless (provider-native wins, exact concatenated text preserved across split chunks — test asserts byte equality); strict mode stays on (`strictFeatureValidation:true`) because normalization happens BEFORE the SDK sees chunks.
**Probe:** `agent-runtime/test/rpc-model-provider.test.ts` — "rejects conflicting canonical models in one Auto response", "captures Auto's canonical model from a later stream page", "normalizes an empty streamed tool argument payload to an object"; `agent-runtime/test/sdk-tool-loop.test.ts` "preserves observed reasoning_content for an unlisted model alias" (asserts exact text `"I should check the skills list first."`, `reasoning === undefined`). rpc-model-provider suite runner-blocked at pin; test names/ranges read directly.

## Get live surrounding code
**Retrieve:** executed at pin (top hits = target family):
```
search_graph({ project:"os-clovy", query:"auto model resolution reasoning content wire format stream chunks", file_pattern:"agent-runtime/*" })
→ src.rpc-model-provider.ReasoningWireFormat Type rpc-model-provider.ts 21-21  (rank 1)
   src.rpc-model-provider.normalizeReasoningContent Function rpc-model-provider.ts 198-224
   src.rpc-model-provider.restoreReasoningContent Function rpc-model-provider.ts 261-271
   src.rpc-model-provider.RpcChatCompletionsModelProvider.streamChunks Method rpc-model-provider.ts 74-134
```

## Verdict
Adopt fail-loud single-canonical-model enforcement, the sticky wire-format latch, and pre-SDK normalization (it lets you keep strict validation). Adapt the prefix tags and the concrete-model charset rule to your catalog. Omit the June-compat prefixes only together with the host-side router that understands them.
