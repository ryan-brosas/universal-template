<!-- capsule-v2 -->
# UI→model message conversion — how does a client UIMessage history become provider-valid ModelMessages with exactly one result per tool call?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** Which parts convert, which synthesize results, and why do step boundaries force message splits?

## convertToModelMessages
**Path/Symbol:** `packages/ai/src/ui/convert-to-model-messages.ts:convertToModelMessages` (:47-442).
**Signature:** `convertToModelMessages(messages, {tools?, ignoreIncompleteToolCalls?, convertDataPart?}): Promise<ModelMessage[]>`.
**Data Shape:** consumes UIMessage parts (text/file/reasoning/tool-*/data/step-start/custom/source); emits `system`/`user`/`assistant`/`tool` ModelMessages; assistant content may embed `tool-call` + `tool-result` (provider-executed) while a FOLLOWING `tool` role message carries client-executed results.

### Decisive source
```ts
// step-start is a HARD boundary: flush the accumulated block into an
// assistant message (+ its tool message) before continuing:
for (const part of message.parts) {
  if (isTextUIPart(part) || isToolUIPart(part) || /* ... */) block.push(part);
  else if (part.type === 'step-start') await processBlock();
}
await processBlock(); // trailing block
// inside processBlock — provider-executed results ride in the ASSISTANT message:
if (part.providerExecuted === true && (state==='output-available' || state==='output-error'))
  content.push({ type: 'tool-result', output: await createToolModelOutput({...}), ... });
// ...and are then SKIPPED in the tool message to avoid duplicates:
// For provider-executed tools, the tool result is already in the assistant
// content. Skip adding to tool message to avoid duplicates (which would create
// orphaned function_call_output entries).
if (toolPart.providerExecuted === true) continue;
// denied approvals synthesize a result so nothing dangles:
if (toolPart.state === 'approval-responded' && toolPart.approval?.approved === false)
  content.push({ type:'tool-result', output: { type:'execution-denied', reason }, ... });
```

**Flow:** optional pre-filter drops tool parts not in a settled state when `ignoreIncompleteToolCalls` (:59-71) → system merges text parts + unions their providerMetadata → user maps text/file/data (file honors `providerReference` → reference data vs url; data parts go through user-supplied `convertDataPart`, undefined ⇒ dropped) → assistant accumulates parts into blocks split at every `step-start`; each block emits ONE assistant message (text/reasoning/file/custom + non-streaming tool-calls; `input-streaming` calls are EXCLUDED :214) then ONE tool message containing approval responses, `execution-denied` synthetic results, and client-executed outputs (`output-error` uses `errorText` with errorMode 'text' here but 'json' for provider-executed inline results :264) → unknown roles throw MessageConversionError.
**Invariant:** every tool call that reaches the model must have exactly one outcome (result / error-text / execution-denied) or providers like OpenAI reject the follow-up request with orphaned `function_call_output`. The providerExecuted duplicate-prevention is the complement of the assistant-inline rule — porting one half without the other either loses results or doubles them. Step-start splitting exists because multi-step generations replay as separate assistant turns.
**Probe:** `packages/ai/src/ui/convert-to-model-messages.test.ts` (3,629 lines; approval/denial/provider-executed matrix).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "convertToModelMessages processBlock step-start createToolModelOutput", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the block-splitting at step boundaries, single-outcome-per-call accounting, and the providerExecuted inline/skip duality. Adapt part-type names and errorMode choices to your schema. Omit source-url/document parts only if your protocol lacks them (they are dropped silently here).
