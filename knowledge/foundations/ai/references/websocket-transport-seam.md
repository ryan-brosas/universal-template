<!-- capsule-v2 -->
# WebSocket transport seam — how does a provider-agnostic WS layer keep message order across async decoding while never throwing from its own callbacks?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What does the transport-generic layer own (constructor resolution, header hygiene, abort wiring, decoding) versus what do callers own, and why is there a promise tail?

## connectToWebSocket
**Path/Symbol:** `packages/provider-utils/src/connect-to-websocket.ts:connectToWebSocket` (:25-132), type `WebSocketConnection` (:9-17).
**Signature:** `connectToWebSocket({url, protocols?, headers?, webSocket?, abortSignal?, onOpen?, onMessageText, onProcessingError, onSocketError?, onClose?, onAbort?}): WebSocketConnection` — `{socket: WebSocketLike | undefined, close(code?)}`.
**Data Shape:** `socket` is undefined when the constructor threw OR the signal was already aborted (both funnel to callbacks instead of throwing). All handler failures route to `onProcessingError`; `close` unregisters the abort listener then closes the socket and NEVER throws.

### Decisive source
```ts
// Messages are processed through a promise tail so async decoding (e.g.
// Blob frames) cannot reorder them, and error/close handling cannot
// overtake a still-decoding terminal frame.
let tail: Promise<void> = Promise.resolve();
socket.onmessage = event => {
  tail = tail
    .then(() => readWebSocketMessageText(event.data))
    .then(text => onMessageText(text))
    .catch(onProcessingError);
};
socket.onerror   = () => { tail = tail.then(() => onSocketError?.()).catch(onProcessingError); };
socket.onclose   = event => {
  const code = typeof closeEvent?.code === 'number' ? closeEvent.code : undefined;
  const reason = typeof closeEvent?.reason === 'string' ? closeEvent.reason : undefined;
  tail = tail.then(() => onClose?.({ code, reason })).catch(onProcessingError);
};
```
```ts
if (abortSignal?.aborted) { onAbort?.(reason); return { socket: undefined, close }; } // no socket at all
// native `WebSocket` ignores the headers option; header-capable implementations like `ws`
// forward it and throw on undefined values:
socket = new WebSocketConstructor(url, protocols, { headers: removeUndefinedEntries(headers ?? {}) });
```

**Flow:** already-aborted check BEFORE construction → constructor in try/catch → abort listener ({once:true}) → event handlers chained onto the shared `tail` promise → `close` removes listener first so post-close aborts don't fire (`onAbort` "not after close" is test-pinned).
**Invariant:** FIFO ordering survives async frame decoding — Blob→text is awaited INSIDE the chain, so a slow frame can delay but never reorder or let a subsequent error/close callback overtake it; naive direct-call handlers break transcript order for any provider streaming large final frames. Header values are stripped of `undefined` entries because header-capable WS implementations throw on them while browsers silently ignore headers entirely. Every failure lands in `onProcessingError`; this function itself never rejects.
**Probe:** `packages/provider-utils/src/connect-to-websocket.test.ts:35` (protocols + undefined-stripped headers reach constructor), `:50` (constructor throw ⇒ onProcessingError + no socket), `:69/:86` (already-aborted no-socket; abort fires once and NOT after close), `:111` (decode failure routed), `:151/:166` (close code/reason extracted; non-standard shapes ignored), `:197` ("process messages in order and run close after pending messages" — Blob+string+close ordering pinned).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"connectToWebSocket promise tail removeUndefinedEntries readWebSocketMessageText","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the promise-tail ordering discipline, pre-construction abort branch, and never-throw close; adapt the auth channel choice (subprotocols vs headers) per provider — callers own it by design; omit close-diagnostics typing if your transport lacks CloseEvent. Consumers: openai/gateway/xai/cartesia/elevenlabs transcription + speech models. Fully direct-test-pinned at this HEAD.
