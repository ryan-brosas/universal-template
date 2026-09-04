<!-- capsule-v2 -->
# SSE response family — how does a chunk stream become an HTTP Response (and Node ServerResponse), and how does an observer tap the wire WITHOUT slowing it?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the exact byte shape on the wire, which headers are contract, and how do you tee the encoded stream for logging without blocking the response?

## JsonToSseTransformStream + createUIMessageStreamResponse + pipeUIMessageStreamToResponse
**Path/Symbol:** `packages/ai/src/ui-message-stream/json-to-sse-transform-stream.ts:JsonToSseTransformStream` (:6-17 whole); `create-ui-message-stream-response.ts:createUIMessageStreamResponse` (:19-44); `pipe-ui-message-stream-to-response.ts:pipeUIMessageStreamToResponse` (:21-52); headers `ui-message-stream-headers.ts:UI_MESSAGE_STREAM_HEADERS` (7L).
**Signature:** Response family: `({stream: ReadableStream<UIMessageChunk>, status?, statusText?, headers?, consumeSseStream?}): Response | Promise<void>`.

### Decisive source
```ts
// JsonToSseTransformStream — the ENTIRE wire encoding:
transform(part, controller) { controller.enqueue(`data: ${JSON.stringify(part)}\n\n`); },
flush(controller)          { controller.enqueue('data: [DONE]\n\n'); },

// consumeSseStream tap — identical in both response adapters:
if (consumeSseStream) {
  const [stream1, stream2] = sseStream.tee();
  sseStream = stream1;
  consumeSseStream({ stream: stream2 }); // no await (do not block the response)
}

// UI_MESSAGE_STREAM_HEADERS — five lines, one of them is a version pin:
'content-type': 'text/event-stream', 'cache-control': 'no-cache', connection: 'keep-alive',
'x-vercel-ai-ui-message-stream': 'v1',
'x-accel-buffering': 'no', // disable nginx buffering
```

**Flow:** chunk stream → SSE transform (`data: <json>\n\n` per object, `[DONE]` sentinel on flush) → optional tee for the observer → TextEncoderStream → Response body (web) / writeToServerResponse (Node); caller headers merge over the defaults via prepareHeaders.
**Invariant:** (1) The tee happens AFTER JSON-to-SSE but BEFORE encoding — observers receive IDENTICAL string bytes to the client (test :174 'received the same data'), and the tap callback is fire-and-forget BY CONTRACT (`// no await`; tests :190 'should not block the response when consumeSseStream takes time' and :239 synchronous variant). Teeing the pre-SSE chunk stream would give observers unencoded objects and back-pressure coupling to the client. (2) `x-vercel-ai-ui-message-stream: v1` is a PROTOCOL VERSION header — clients can feature-detect the chunk grammar; dropping it makes version negotiation impossible (asserted in create-ui-message-stream-response.test.ts:45). (3) `x-accel-buffering: no` exists because nginx buffers SSE by default and buffered chat renders as nothing-then-everything. (4) `[DONE]` is emitted in flush — a stream that errors before flush sends NO sentinel, mirroring the ingestion-side swallow of `[DONE]` (pass 5 event-ingestion capsule). Porters who encode before teeing double-encode for observers; porters who await the tap couple logging latency into TTFB.

**Probe:** `bash -c "grep -n 'x-vercel-ai-ui-message-stream' $REFERENCE_ROOT/ai/packages/ai/src/ui-message-stream/ui-message-stream-headers.ts && grep -rn 'do not block the response' $REFERENCE_ROOT/ai/packages/ai/src/ui-message-stream/create-ui-message-stream-response.ts $REFERENCE_ROOT/ai/packages/ai/src/ui-message-stream/pipe-ui-message-stream-to-response.ts"` → `:5`, `:36` + `:40`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "readUIMessageStream uiMessageChunkSchema getResponseUIMessageId JsonToSseTransformStream createAgentUIStream", limit: 5 });
// → ai.packages.ai.src.ui-message-stream.json-to-sse-transform-stream.JsonToSseTransformStream Class :6-17
```

## Verdict
Adopt the `data: <json>\n\n` + `[DONE]` frame, post-encode tee with un-awaited observer, and the version-pinned header set. Adapt headers to your proxy topology (keep the buffering disable). Omit pipeUIMessageStreamToResponse on non-Node hosts.
