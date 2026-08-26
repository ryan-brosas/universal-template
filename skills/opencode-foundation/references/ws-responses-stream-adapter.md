<!-- capsule-v2 -->
# Responses-over-WebSocket stream adapter — how do WS JSON events become an SSE Response, and what closes the stream?

**Source:** opencode (Slate-licensed monorepo) @ `dev@0352100` (NEW file `plugin/openai/ws.ts`, drift wave 4643e65→0352100). **Question:** What is the exact wire protocol and terminal-state grammar for streaming OpenAI Responses over a WebSocket into a fetch-shaped SSE Response?

## Protocol constants & framing
**Path/Symbol:** `packages/opencode/src/plugin/openai/ws.ts` (`PROTOCOL_HEADER` :11, `streamResponsesWebSocket` :139-342, `parseWrappedError` :344-362, `attach()` :300-318).
**Signature:** `streamResponsesWebSocket({socket, body, idleTimeout?, signal?, onFirstEvent?, onComplete?, onTerminal?, onRetryableTerminal?, onConnectionInvalid?, onAbort?}) → Response (SSE)`; connect side: `connectResponsesWebSocket({url, headers, timeout?, signal?}) → Promise<WebSocket>` with `openai-beta: responses_websockets=2026-02-06`.
**Data Shape:** request = one JSON frame `{type:"response.create", …body}` with `stream`/`background` keys STRIPPED (:311); each inbound text frame is re-emitted as SSE `data: <line>\n\n` per source line (:242-249); completion enqueues literal `data: [DONE]\n\n` then closes (:160-164).

### Decisive source
```ts
// ws.ts:255-267 — the terminal-state grammar: only these frames end the stream
if (event.type === "response.completed" || event.type === "response.done") {
  completed = true; options.onComplete?.(event); options.onTerminal?.(event)
  closeCompleted()                       // enqueue "data: [DONE]" + close
  return
}
if (event.type === "response.failed" || event.type === "response.incomplete" || event.type === "error") {
  completed = true; options.onTerminal?.(event)
  closeCompleted()                       // ends CLEANLY — pool treats non-completed as unhealthy
}
```

**Flow:** attach ⇒ send response.create ⇒ idle timer arms around BOTH send and wait ("idle timeout sending/waiting for websocket") ⇒ each event resets it. `type:"error"` frames take the RETRYABLE branch first: cleanup socket, call `onRetryableTerminal(event)` — returning a NEW WebSocket swaps it in via `attach(next)` mid-stream and re-sends response.create (pool passes a handler that throws ONLY on connection-limit errors); other error shapes flow to `parseWrappedError`, which converts status-bearing errors (∉2xx) into APICallError on the stream (:222-238). Socket close BEFORE terminal ⇒ invalidate(ResponseStreamError, closeCode) — pool reads closeCode 1009 as message-too-big ⇒ instant HTTP fallback. Abort/cancel terminate the socket and error the controller with AbortError; binary frames invalidate immediately.
**Invariant:** `completed` is a one-shot latch checked at EVERY entry point — after it flips, late messages/errors are ignored, guaranteeing single-terminal semantics. The idle timeout is the ONLY watchdog (no ping/pong): a silent server dies at idleTimeout. Terminal `response.failed/incomplete/error` close the SSE stream NORMALLY (with [DONE]) rather than erroring it — the POOL, not the adapter, decides health via its onTerminal callback.
**Probe:** direct test pins — `packages/opencode/test/plugin/openai-ws.test.ts`: ":75 streams websocket events as SSE and handles response.done", ":105 errors the SSE stream when the server closes before a terminal event", ":129 rejects unexpected binary websocket frames", ":422 retries websocket connection limit errors on the next stream attempt"; source pins:
```bash
grep -n 'responses_websockets=2026-02-06' packages/opencode/src/plugin/openai/ws.ts
grep -n 'data: \[DONE\]' packages/opencode/src/plugin/openai/ws.ts
```
expect one hit each (:11, :162).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "streamResponsesWebSocket response.create terminal idle", limit: 8 });
```

## Verdict
Adopt the single-frame request / SSE-framed response bridge, the terminal-frame grammar, and completed-latch single-terminal discipline; adapt protocol version header and frame types per provider spec; omit Bun proxy workaround details unless targeting Bun.
