<!-- capsule-v2 -->
# Gateway transcription WS stream — how does a duplex audio pump over one socket survive error parts, aborts, and close-before-finish?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the frame lifecycle of streaming transcription, and which terminal conditions must the client distinguish?

## ReadableStream pump over connectToWebSocket
**Path/Symbol:** `packages/gateway/src/gateway-transcription-model.ts:createGatewayTranscriptionStream` (219–396) + `sendAudio` (259–291) + `SERVER_ERROR_STATUS_CODES` (383–391).
**Signature:** `function createGatewayTranscriptionStream({...}): ReadableStream<TranscriptionModelV4StreamPart>`.
**Data Shape:** Client→server frames: JSON start frame (`{type: start, inputAudioFormat, providerOptions?, includeRawChunks?}` — optional keys OMITTED so the frame stays minimal), binary audio frames split to ≤64 KiB with `waitForWebSocketBufferDrain` backpressure between sends, then `{type: 'audio-done'}`. Server→client: envelope-serialized stream parts via `parseTranscriptionStreamPart` (unknown types silently skipped = forward compat). Terminal states: `finish` part → enqueue+close+`cleanup(1000)`; `error` part → stopAudio but KEEP stream open until server closes (billing flush window); raw socket close without finish → synthetic error.

### Decisive source
```ts
const MAX_AUDIO_FRAME_BYTES = 64 * 1024;
// …
if (part.type === 'error') {
  hasServerErrorPart = true; lastServerError = part.error;
  // envelope rule 5: error parts are terminal — stop sending audio
  // while the server holds the connection open (e.g. for its final billing flush)
  stopAudio();
}
// …on finish:
finished = true; controller.enqueue(part); controller.close(); cleanup(1000);
// …onClose with remembered server error → typed Gateway error, not generic:
SERVER_ERROR_STATUS_CODES = { authentication_error: 401, failed_dependency: 424, forbidden: 403,
  internal_server_error: 500, invalid_request_error: 400, model_not_found: 404, rate_limit_exceeded: 429 };
```

**Flow:** doStream builds headers (auth method parsed BEFORE any async gap) + subprotocols from resolved Authorization header (case-insensitive via normalizeHeaders) → connectToWebSocket opens → start frame → sendAudio pump → parts relayed → exactly one terminal path fires cleanup.
**Invariant:** The `finished` latch guards EVERY terminal path (finish/error/abort/cancel/socket-error/close) so cleanup and controller.error run at most once. Reader-vs-stream cleanup duality: if `sendAudio` took a reader, cancel the READER; if failure happened pre-open, cancel the caller's STREAM directly — else an upstream producer hangs. Auth rides subprotocols because browser WebSocket cannot set headers; header-capable custom WebSockets still receive full headers.
**Probe:** `grep -c 'cleanup(1000)' packages/gateway/src/gateway-transcription-model.ts` → `1`; `grep -cF 'model_not_found: 404,' packages/gateway/src/gateway-transcription-model.ts` → `1`; direct tests: gateway-transcription-model.test.ts 'should split audio chunks larger than the maximum frame size', :571 `expect(ws.close).toHaveBeenCalledWith(1000)`, 'should stop sending audio after a server error part while keeping the stream open until close', 'should cancel the audio stream when the connection fails before open'.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createGatewayTranscriptionStream sendAudio MAX_AUDIO_FRAME_BYTES", limit: 10 });
```
Resolves line-exact: `createGatewayTranscriptionStream Function gateway-transcription-model.ts 219-396`.

## Verdict
Adopt the single-latch duplex pump with reader/stream cleanup duality and the error-part-then-wait-for-close protocol; adapt frame size and status map to your envelope rules; omit nothing — each terminal branch corresponds to a shipped test.
