<!-- capsule-v2 -->
# UI chunk reducer — how does a UIMessageChunk stream fold into an assistant message without duplicating parts or losing cross-step tool calls?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What are the lookup, mutation, and error rules for each chunk type so a porter's reducer matches the wire semantics exactly?

## processUIMessageStream
**Path/Symbol:** `packages/ai/src/ui/process-ui-message-stream.ts:processUIMessageStream` (:82-992); state factory `createStreamingUIMessageState` (:56-80).
**Signature:** `processUIMessageStream({stream, messageMetadataSchema?, dataPartSchemas?, runUpdateMessageJob, onError, onToolCall?, onData?}): ReadableStream` — a TransformStream; every chunk is re-enqueued AFTER processing (:987).
**Data Shape:** `StreamingUIMessageState = {message, activeTextParts, activeReasoningParts, partialToolCalls (id → {text,index,toolName,dynamic,title,toolMetadata}), finishReason}`; the id maps are prototype-less (`createIdMap`).

### Decisive source
```ts
// step-scoped FIRST, whole-message fallback — a later step may stream results
// for a call opened in an earlier one:
function getToolInvocation(toolCallId) {
  let t = getCurrentStepParts().filter(isToolUIPart).find(i => i.toolCallId === toolCallId);
  if (t == null) { /* scan parts BACKWARD for the id */ }
  if (t == null) throw new UIMessageStreamError({chunkType:'tool-invocation', ...}); // unknown id ⇒ DATA-shaped error part, not a throw
}
// sticky flag + metadata split inside updateToolPart:
anyPart.providerExecuted = anyOptions.providerExecuted ?? part.providerExecuted; // once set, stays for streaming
if (providerMetadata != null) {
  if (options.state === 'output-available' || options.state === 'output-error')
       resultPart.resultProviderMetadata = providerMetadata;   // result rides on output states
  else  part.callProviderMetadata = providerMetadata;          // otherwise it is CALL metadata
}
// transient data parts reach onData but never enter the message:
if (dataChunk.transient) { onData?.(dataChunk); break; }
// start-step pushes the boundary WITHOUT write(); finish-step resets BOTH active maps:
case 'start-step': state.message.parts.push({type:'step-start'}); break;
case 'finish-step': state.activeTextParts = createIdMap(); state.activeReasoningParts = createIdMap(); break;
```

**Flow:** every chunk handled INSIDE `runUpdateMessageJob` (serialized upstream by chat.ts) → text/reasoning open as `{state:'streaming'}` parts registered in id maps, deltas mutate in place, end marks `'done'` and deletes the map entry (delta/end for a missing id ⇒ UIMessageStreamError with remediation text :443-449,:505-511) → tool-input-start seeds `partialToolCalls[toolCallId]`, deltas accumulate raw JSON text and re-parse via `parsePartialJson` EVERY delta into live `input-streaming` input → static vs dynamic tools take parallel update helpers (`updateToolPart`/`updateDynamicToolPart`) keyed by `type: 'tool-${name}'` vs `'dynamic-tool'`; tool-input-error honors an existing part's type to avoid duplicates with mismatched type (:705-716) → tool-input-available fires blocking `onToolCall` ONLY for non-provider-executed calls (:697-701) → approval chunks mutate the SAME tool part (`approval-requested` → `approval-responded` preserving `isAutomatic`+`signature`; `output-denied`) → metadata merges via `mergeObjects` + schema validation per update → unknown chunk types fall to the default branch and are IGNORED unless they are data chunks.
**Invariant:** parts are mutated IN PLACE (by reference) between writes — replacing instead of mutating breaks React identity-based memoization downstream AND breaks `getToolInvocation`'s backward scan assumptions. The current-step window is everything after the LAST `step-start`. `providerExecuted` never un-sets mid-stream.
**Probe:** `packages/ai/src/ui/process-ui-message-stream.test.ts:4872` ("should not call the update function with the transient part"), suite at 9,451 lines incl. inline-snapshot write-call sequences per chunk type.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "processUIMessageStream StreamingUIMessageState updateToolPart tool-input-delta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier lookup, in-place mutation + write-per-chunk protocol, sticky providerExecuted, call/result metadata split, transient-part bypass, and error-as-data for unknown ids. Adapt chunk type names to your protocol. Omit nothing behavioral — this reducer IS the client contract.
