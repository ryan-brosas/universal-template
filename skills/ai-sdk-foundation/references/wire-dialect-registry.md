<!-- capsule-v2 -->
# Wire dialect registry — which transport subclasses exist, what does the ChatTransport interface owe its implementors, and where do re-export shims end?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the complete transport family a porter must choose between (or extend), and what belongs in each layer?

## The transport family
**Path/Symbol:** interface `packages/ai/src/ui/chat-transport.ts:ChatTransport` (:15-86); base HTTP impl `http-chat-transport.ts:HttpChatTransport` (capsule `http-chat-transport`, pass 7); three subclasses: `default-chat-transport.ts:DefaultChatTransport` (:12-36), `text-stream-chat-transport.ts:TextStreamChatTransport` (:9-23), `direct-chat-transport.ts:DirectChatTransport` (:55-143, capsule `direct-in-process-transport`).
**Signature:** `interface ChatTransport<UI_MESSAGE extends UIMessage> { sendMessages({trigger, chatId, messageId, messages, abortSignal} & ChatRequestOptions): Promise<ReadableStream<UIMessageChunk>>; reconnectToStream({chatId, abortSignal} & ChatRequestOptions): Promise<ReadableStream<UIMessageChunk> | null>; }`.

### Decisive source
```ts
// default-chat-transport.ts:19-35 — UI wire dialect = SSE-framed JSON chunks:
protected processResponseStream(stream) {
  return parseJsonEventStream({ stream, schema: uiMessageChunkSchema })
    .pipeThrough(new TransformStream<ParseResult<UIMessageChunk>, UIMessageChunk>({
      async transform(chunk, controller) {
        if (!chunk.success) { throw chunk.error; }   // parse failure = stream error
        controller.enqueue(chunk.value);
      },
    }));
}
// text-stream-chat-transport.ts — plain-text dialect: bytes→TextDecoderStream
// →transformTextToUiMessageStream. direct-chat-transport.ts — no wire at all.
```

**Flow:** `HttpChatTransport` owns everything wire-EXCEPT decoding (Resolvable option resolution, header layering, prepare hooks, resume GET + 204 semantics — all pass 7) and exposes exactly one template-method hook: `processResponseStream(bytes) => ReadableStream<UIMessageChunk>`. Each dialect is then a constructor-plus-one-method subclass: Default = SSE JSON with zod-validated chunks where an unparseable frame THROWS mid-transform (the reducer never sees garbage), Text = synthetic framing over raw deltas, Direct = full in-process bypass. The interface contract every implementor owes: `reconnectToStream` returns null for "nothing to resume" (Direct documents this explicitly) and sendMessages may throw on request failure.
**Invariant:** new wire protocols cost ONE method override — porters who instead subclass at the AbstractChat level reimplement option plumbing they already have. Chunk validation happens AT THE WIRE BOUNDARY only (Default's schema gate); after that, chunks are trusted — moving validation into the reducer would silently change error semantics for every dialect. Boundary of this capsule: `packages/ai/src/ui/index.ts` is a pure re-export shim (no logic — omit-with-reason); `enrich-chat-messages.ts` does not exist at HEAD; `convert-file-list-to-file-ui-parts.ts` is already owned by pass-7 `filelist-ingestion.md`.

**Probe:** `grep -n "if (!chunk.success)" /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui/default-chat-transport.ts && grep -c "it(" /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui/direct-chat-transport.test.ts` → :28 and 7.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "DefaultChatTransport TextStreamChatTransport processResponseStream parseJsonEventStream uiMessageChunkSchema", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the template-method split (transport plumbing in the base class, dialect in one override) and wire-boundary-only chunk validation. Adapt dialects to your framing. Omit further transports unless you add a protocol the SDK lacks.
