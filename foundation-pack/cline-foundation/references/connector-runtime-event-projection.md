<!-- capsule-v2 -->
# Runtime-event projection — how does a chat platform turn hub stream events into reply text without corrupting or duplicating the stream?

**Source:** cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** How do I bridge a push-based runtime event stream into a pull-based reply iterator while keeping streamed text monotonic, failures single-shot, and side channels (tool status, media, approvals) out of the text?

## Push/pull bridge over a single-slot notify queue
**Path/Symbol:** `apps/cli/src/connectors/runtime-turn.ts:createConnectorRuntimeTurnStream` (:84-360).
**Signature:** `createConnectorRuntimeTurnStream(input: { client: HubSessionClient; sessionId: string; request: ChatRunTurnRequest; clientId: string; logger: CliLoggerAdapter; transport: string; conversationId: string; onToolStatus?; onApprovalRequested?; onMedia?; onCompleted?; onFailed? }): AsyncIterable<string>`.
**Data Shape:** QueueItem = `{type:"chunk",value} | {type:"error",error} | {type:"end"}`; one `notify` slot (resolved then immediately cleared); `streamedText` accumulates; `failed` and `closed` latches.

### Decisive source
```ts
const push = (item: QueueItem) => {
	queue.push(item);
	notify?.();
	notify = undefined;
};
// resolveTextDelta: accumulated-vs-delta rewind rule
if (typeof accumulated === "string") {
	if (accumulated.startsWith(previous)) {
		return { delta: accumulated.slice(previous.length), nextText: accumulated };
	}
	if (previous.startsWith(accumulated)) {
		return { delta: "", nextText: previous };
	}
}
const text = typeof payload.text === "string" ? payload.text : "";
return { delta: text, nextText: `${previous}${text}` };
```

**Flow:** streamEvents subscribes per sessionId → onEvent routes by eventType: `runtime.chat.text_delta` → resolveTextDelta → push chunk; `runtime.chat.tool_call_start` → postStatus("Executing {name}..."); `runtime.chat.tool_call_end` → postStatus("{name} failed: {err≤240}") ONLY when payload.error is non-empty (successful ends post nothing); `runtime.chat.media` → void onMedia (never the text stream); `approval.requested` → all three ids trimmed+required, missing any ⇒ silently dropped → void onApprovalRequested; `runtime.chat.failed` → failed=true, onFailed, push error. sendRuntimeSession runs with `{timeoutMs: null}`; its `.then` returns early `if (failed)`, fires onCompleted, and pushes only `finalText.slice(streamedText.length)` when finalText startsWith streamedText; `.catch` also returns early `if (failed)`; `.finally` stops streaming and pushes end. Consumer loop awaits notify when empty, yields chunks, throws error items, sets closed on end; its finally stopStreaming()s and awaits runTurn.catch(()=>{}).
**Invariant:** Streamed text is monotonic — a server-side shrink yields delta "" and keeps the longer local text; the first failure source (event or transport) wins via the shared `failed` latch, never doubled; tool status/media/approvals never enter the text stream; a queued turn (no result) is a non-error completion with zero chunks.
**Probe:** `apps/cli/src/connectors/runtime-turn.test.ts` (6 cases/5 distinct: media bypasses text; tool status via callback not text; streaming survives status-delivery failure; queued turn non-error; failed event surfaces normalized error — duplicated pair upstream).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "createConnectorRuntimeTurnStream resolveTextDelta streamEvents text_delta", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-slot-notify bridge, the accumulated-vs-delta rewind rule, the failed-latch first-wins discipline, and the side-channel callback split. Adapt QueueItem/notify to the host's async primitives and the event vocabulary to the host runtime. Omit the hub-specific event type names. Coverage caveat: MCP check_index_coverage not runnable this session (transport failure); suite has one upstream-duplicated case pair.
