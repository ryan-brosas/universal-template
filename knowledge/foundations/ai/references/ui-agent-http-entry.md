<!-- capsule-v2 -->
# Agent HTTP entry — what does the server do between receiving UI messages and returning the SSE stream, and in what order?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the canonical request pipeline for an agent endpoint, and why must validation run even though convertToModelMessages would tolerate the raw input?

## createAgentUIStream (+ response/pipe wrappers)
**Path/Symbol:** `packages/ai/src/agent/create-agent-ui-stream.ts:createAgentUIStream` (:46-118 whole); wrappers `create-agent-ui-stream-response.ts` (74L) and `pipe-agent-ui-stream-to-response.ts:pipeAgentUIStreamToResponse` (:40-77) — both thin `await createAgentUIStream(options)` + response-family calls; helpers `infer-agent-tools.ts` (7L) / `infer-agent-ui-message.ts` (11L) type-only.
**Signature:** `({agent, uiMessages: unknown[], options?, abortSignal?, timeout?, experimental_sandbox?, experimental_transform?, onStepEnd?/onStepFinish?, ...UIMessageStreamOptions}): Promise<AsyncIterableStream<InferUIMessageChunk>>`.

### Decisive source
```ts
const validatedMessages = await validateUIMessages<UI_MESSAGE>({
  messages: uiMessages,
  // tools are compatible; the casting is required because the context param is
  // not available in ui messages
  tools: agent.tools as unknown as {...},
});
const modelMessages = await convertToModelMessages(validatedMessages, { tools: agent.tools });
const result = await agent.stream({ prompt: modelMessages, options, abortSignal, timeout,
                                   experimental_sandbox: sandbox, experimental_transform,
                                   onStepEnd: onStepEnd ?? onStepFinish });
// TODO reading `originalMessages` is here for bc, always use `validatedMessages` in v7
const originalMessages = uiMessageStreamOptions.originalMessages ?? validatedMessages;
return createAsyncIterableStream(
  toUIMessageStream({ ...uiMessageStreamOptions, originalMessages, stream: result.stream, tools: agent.tools }));
```

**Flow:** validate → convert → agent.stream → toUIMessageStream, wrapped in createAsyncIterableStream so the caller gets both ReadableStream and for-await protocols (capsule async-iterable-stream-duality); the two HTTP wrappers add ONLY status/header/tee plumbing from the response family.
**Invariant:** (1) Validation runs FIRST and its output — not the raw input — feeds conversion. The validation ladder (pass 8) enforces tool-input schemas at `input-available`; skipping it here would let hostile client histories skip schema checks that convertToModelMessages itself does not perform (conversion is shape-normalizing, not security). (2) The cast comment (:82-83) documents a deliberate typing seam: agent tools carry a context param that UIMessage-level Tool types cannot express — porters who "fix" the cast by widening Tool break inference instead. (3) Continuation identity flows from `originalMessages ?? validatedMessages` with an explicit v7 TODO (:106-108): passing raw uiMessages here would resurrect unvalidated parts into persistence callbacks. (4) `agent.tools` is passed BOTH to conversion and to toUIMessageStream so provider-executed/dynamic classification (`isDynamic`) sees the same map on the way in and out. (5) Deprecated alias resolution (`onStepEnd ?? onStepFinish`) happens at every layer consistently. This file is the reference ORDERING for the whole stack: everything else mined in passes 1-8 sits inside one of its four steps.

**Probe:** `bash -c "grep -n 'tools are compatible' $REFERENCE_ROOT/ai/packages/ai/src/agent/create-agent-ui-stream.ts && grep -n 'should pass sandbox to tool execution' $REFERENCE_ROOT/ai/packages/ai/src/agent/create-agent-ui-stream-response.test.ts"` → `:82`, `:366`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "readUIMessageStream uiMessageChunkSchema getResponseUIMessageId JsonToSseTransformStream createAgentUIStream", limit: 5 });
// → ai.packages.ai.src.agent.create-agent-ui-stream.createAgentUIStream Function :46-118
```

## Verdict
Adopt the four-step ordering with validation-before-conversion and single-tool-map symmetry. Adapt option names to your API. Omit the wrappers if your framework binds routes differently.
