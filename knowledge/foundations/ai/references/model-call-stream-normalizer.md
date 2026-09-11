<!-- capsule-v2 -->
# Model-call stream normalizer — how does one TransformStream turn provider V4 parts into user-facing parts while accumulating content, resolving approvals, and computing performance stats?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How are raw model stream parts standardized, and which state must the transform keep across chunks?

## streamLanguageModelCall + createLanguageModelV4StreamPartToLanguageModelStreamPartTransform
**Path/Symbol:** `packages/ai/src/generate-text/stream-language-model-call.ts:streamLanguageModelCall` (:193-386), `createLanguageModelV4StreamPartToLanguageModelStreamPartTransform` (:389-767).
**Signature:** `streamLanguageModelCall({...callSettings, tools?, output?, repairToolCall?, refineToolInput?, onStart?, onLanguageModelCallStart/End?, _internal?}): Promise<{stream: AsyncIterableStream<LanguageModelStreamPart>, request?, response?}>`.
**Data Shape:** Cross-chunk state: `toolCallsByToolCallId: Map<string, TypedToolCall>` (provider approval requests + tool results resolve through it), `modelCallContent: ContentPart[]` (accumulated for onLanguageModelCallEnd), `textPartIndexes`/`reasoningPartIndexes: Map<string, number>` (id → index into content array), timing accumulators (`timeToFirstOutputMs`, `previousOutputChunkTimestampMs`, `timeBetweenOutputChunksMs[]`). IDs: `aitxt`/24 (response), `call`/24.

### Decisive source
```ts
case 'tool-approval-request': {
  const toolCall = toolCallsByToolCallId.get(chunk.toolCallId);
  if (toolCall == null) {
    controller.enqueue({ type: 'error',
      error: new ToolCallNotFoundForApprovalError({ toolCallId, approvalId }) });
    break;                                   // unknown reference ⇒ error PART, not throw
  }
  // ... enqueue {type:'tool-approval-request', approvalId, toolCall}
}
case 'tool-result': {                        // provider-executed results arrive WITHOUT a prior
  const toolCall = toolCallsByToolCallId.get(chunk.toolCallId);  // local parse — best-effort join
  const toolResultPart = chunk.isError ? ({ type:'tool-error', input: toolCall?.input,
      error: chunk.result, providerExecuted: true, ... })
    : ({ type:'tool-result', input: toolCall?.input, output: chunk.result,
      providerExecuted: true, ... });        // input may be undefined when unjoinable
}
case 'tool-input-start': {
  const tool = getOwn(tools, chunk.toolName);   // prototype-safe lookup of model-controlled name
  controller.enqueue({ ...chunk, dynamic: chunk.dynamic ?? tool?.type === 'dynamic',
    title: tool?.title, ...(tool?.metadata != null ? { toolMetadata: tool.metadata } : {}) });
}
```

**Flow:** standardizePrompt → convertToLanguageModelPrompt (once per step; onStart REQUIRES the V4 prompt, source comment :260-267) → prepareTools/prepareToolChoice → doStream inside telemetry context → pipeThrough normalizer → createAsyncIterableStream. Normalizer: text/reasoning start-delta-end upsert content parts by id (`upsertTextContentPart` :811-850 creates on first sight, appends deltas, deletes the index at end) → tool-call parses via parseToolCall and STORES in the id map (invalid client-executable calls also emit a synthesized `tool-error`, invalid provider-executed do NOT — test :1048) → finish computes performance `{responseTimeMs, effectiveOutputTokensPerSecond, timeToFirstOutputMs, timeBetweenOutputChunksMs p10/median/p90 nearest-rank}` and emits `model-call-end` after notifying.
**Invariant:** Timing counts ONLY non-empty output chunks (`isOutputChunk` :774-783 checks `.delta.length > 0`) plus files and tool-calls. Provider-emitted approval/tool-result references to unknown ids become `error` PARTS in the stream — never thrown, never silently dropped. The responseId is generated UP FRONT so providers that send none still get a stable one (test :359).
**Probe:** `packages/ai/src/generate-text/stream-language-model-call.test.ts:74` (onLanguageModelCallStart before doStream), `:578/:612/:658` (ttfo + inter-chunk stats), `:1048` (no synthesized error for invalid provider-executed calls), `:1253` (repair path wired), `:1338` (unknown approval id ⇒ error part), `:1397` (approval request joins parsed tool call).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"streamLanguageModelCall upsertTextContentPart ToolCallNotFoundForApprovalError","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the cross-chunk state trio (id→parsedToolCall map, content accumulator, part-index maps) and the error-part-not-throw rule for dangling references; adapt the performance-stat formulas to your telemetry surface; omit the V4-specific part union. Depends on capsules: tool-call-parse-and-repair-ladder, prototype-safe-lookup, swallowing-callback-bus, async-iterable-stream-duality.
