<!-- capsule-v2 -->
# Direct in-process transport — what does it take to run the full chat stack with zero HTTP, and why must an un-resumable transport return null instead of throwing?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How does a ChatTransport implementation bridge client history to an in-process agent while preserving validation, aborts, options, and stream shaping?

## DirectChatTransport
**Path/Symbol:** `packages/ai/src/ui/direct-chat-transport.ts:DirectChatTransport` (143L whole): `sendMessages` (:89-130), `reconnectToStream` (:138-142). Implements the two-method `ChatTransport` interface (`packages/ai/src/ui/chat-transport.ts`:15-86 — `sendMessages({trigger:'submit-message'|'regenerate-message', chatId, messageId, messages, abortSignal} & ChatRequestOptions) => Promise<ReadableStream<UIMessageChunk>>`; `reconnectToStream(...) => Promise<ReadableStream | null>`).
**Signature:** `new DirectChatTransport({agent, options?, ...UIMessageStreamOptions-minus-onFinish})`.

### Decisive source
```ts
// sendMessages — the whole pipeline is FOUR awaited steps:
const validatedMessages = await validateUIMessages<UI_MESSAGE>({ messages,
  // tools are compatible; the casting is required because the context param is
  // not available in ui messages
  tools: this.agent.tools as unknown as {...InferUIMessageTools mapping...} });
const modelMessages = await convertToModelMessages(validatedMessages, { tools: this.agent.tools });
const result = await this.agent.stream({ prompt: modelMessages, abortSignal,
  ...(this.agentOptions !== undefined ? { options: this.agentOptions } : {}) });
return toUIMessageStream({ ...this.uiMessageStreamOptions, stream: result.stream, tools: this.agent.tools });
// reconnectToStream — deliberate total function:
// Direct transport does not support reconnection since there is no
// persistent server-side stream to reconnect to.  @returns Always returns `null`
async reconnectToStream(_) { return null; }
```

**Flow:** constructor captures agent + call options + stream options (onFinish deliberately OMITTED from the option surface — the transport returns a stream; finish handling belongs to the caller) → sendMessages validates untrusted history against the AGENT's tool schemas (cast documented as required because runtime context isn't expressible on UIMessage types) → converts UI→model messages (capsule `ui-to-model-conversion`) → streams from the agent passing the caller's abortSignal through → wraps the raw model stream into a UIMessageChunk stream via `toUIMessageStream` with agent tools attached.
**Invariant:** null is the PROTOCOL answer for "nothing to resume" — AbstractChat treats null reconnect as silent no-op (pass-7 `chat-request-lifecycle`: reconnect probed before submitted-flip so page-load never flashes), whereas a thrown error would mark the chat errored on every page reload of an in-process app. Validation is NOT skipped for speed: running the same validate→convert ladder as the HTTP server route means invalid history fails identically in-process and over the wire. The sibling transports complete the family: `TextStreamChatTransport` overrides only `processResponseStream` (`text-stream-chat-transport.ts`:16-22 — bytes→TextDecoderStream→`transformTextToUiMessageStream`) and `DefaultChatTransport` swaps in `parseJsonEventStream` + `uiMessageChunkSchema` where failed parse results are THROWN from the transform step (`default-chat-transport.ts`:19-35) — template-method subclassing over HttpChatTransport means a new wire dialect costs exactly one method override.

**Probe:** `bash -c "grep -n \"should convert UI messages to model messages correctly\\|should throw error for invalid messages\\|should return null\" /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui/direct-chat-transport.test.ts"` → :318, :404, :427.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "DirectChatTransport sendMessages reconnectToStream ChatTransport", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the four-step pipeline (validate → convert → agent.stream → toUIMessageStream) and the null-not-throw reconnect contract. Adapt the agent seam to your own orchestrator. Omit the generic type parameters if your language erases them — they carry no runtime behavior.
