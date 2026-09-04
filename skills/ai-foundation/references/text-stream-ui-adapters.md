<!-- capsule-v2 -->
# Plain-text stream adapters — how does a bare token stream masquerade as a full UI message stream, and where does the synthetic frame get its ids?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you lift raw text deltas into the UIMessageChunk protocol (and back down for legacy consumers) without breaking chunk-reducer or SSE clients?

## transformTextToUiMessageStream + TextStreamChatTransport
**Path/Symbol:** `packages/ai/src/ui/transform-text-to-ui-message-stream.ts:transformTextToUiMessageStream` (27L whole); consumer `packages/ai/src/ui/text-stream-chat-transport.ts:TextStreamChatTransport.processResponseStream` (:16-22).
**Signature:** `transformTextToUiMessageStream({stream: ReadableStream<string>}): ReadableStream<UIMessageChunk>`.

### Decisive source
```ts
return stream.pipeThrough(new TransformStream<string, UIMessageChunk>({
  start(controller) {                       // frame opens BEFORE any data:
    controller.enqueue({ type: 'start' });
    controller.enqueue({ type: 'start-step' });
    controller.enqueue({ type: 'text-start', id: 'text-1' });   // CONSTANT id
  },
  async transform(part, controller) {
    controller.enqueue({ type: 'text-delta', id: 'text-1', delta: part });
  },
  async flush(controller) {                 // close sequence mirrors the open:
    controller.enqueue({ type: 'text-end', id: 'text-1' });
    controller.enqueue({ type: 'finish-step' });
    controller.enqueue({ type: 'finish' });
  },
}));
```

**Flow:** `start` enqueues the three framing chunks before the first delta ever arrives; every source chunk becomes exactly one `text-delta` under the constant part id `text-1`; `flush` closes text → step → stream in reverse order. The empty-stream case still emits all six framing chunks (`transform-text-to-ui-message-stream.test.ts`:56-86) — a well-formed empty assistant message, not silence.
**Invariant:** the reducer (`process-ui-message-stream`, pass 7) keys text parts by id — one stream ⇒ ONE text part with id `text-1`; per-chunk unique ids would shatter the message into N parts. The start/open + flush/close symmetry is what lets the SAME bytes feed both UIMessage clients and plain-text consumers downstream. `TextStreamChatTransport` shows the integration shape: subclass HttpChatTransport and override ONLY `processResponseStream` (`stream.pipeThrough(new TextDecoderStream())` first — this transform takes STRINGS, not bytes). The decode-side twin `processTextStream` (`packages/ai/src/ui/process-text-stream.ts`:1-16) is the minimal inverse: `pipeThrough(new TextDecoderStream()).getReader()` + while-read loop awaiting each `onTextPart` callback sequentially — used by the legacy completion plane (`call-completion-api.ts`:91), NOT by transports.

**Probe:** `bash -c "grep -n \"should handle empty streams correctly\" $REFERENCE_ROOT/ai/packages/ai/src/ui/transform-text-to-ui-message-stream.test.ts && grep -c 'text-1' $REFERENCE_ROOT/ai/packages/ai/src/ui/transform-text-to-ui-message-stream.test.ts"` → :56 and ≥6.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "transformTextToUiMessageStream TextStreamChatTransport processTextStream", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt the six-chunk envelope with constant text-part id and mirrored open/close ordering. Adapt chunk type names to your protocol. Omit processTextStream if your platform has no legacy text-hook surface.
