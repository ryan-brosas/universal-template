<!-- capsule-v2 -->
# acp-agent-event-streaming-contract — how do you stream agent runtime events to a protocol client without double-sending or blocking the runtime?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** Which runtime events become protocol notifications, when does each payload fly, and who settles a tool call?

## Payload-at-start, terminal-at-end; fire-and-forget sends; media only at end; fatal errors never ride this channel
**Path/Symbol:** `apps/cli/src/acp/session-updates.ts` (`forwardAgentEvent` :15-21, `translateEvent` :23-41, `translateContentStart` :43-73, `translateContentEnd` :97-146, `describeAgentError` :75-78).
**Signature:** `forwardAgentEvent(conn: AgentSideConnection, sessionId: string, event: AgentEvent): void` — synchronous, never awaited by the caller.
**Data Shape:** In: one `AgentEvent` (content_start/content_end × contentType text|reasoning|tool|media, plus done/error/iteration_*/usage). Out: zero-or-more `SessionUpdate` objects; each sent via `void conn.sessionUpdate(...)` (4 void-send sites in the file, including the three auxiliary senders).

### Decisive source
```ts
function translateEvent(event: AgentEvent): SessionUpdate[] {
	switch (event.type) {
		case "content_start": return translateContentStart(event);
		case "content_end":   return translateContentEnd(event);
		case "done": case "error": return [];
		case "iteration_start": case "iteration_end": case "usage": return [];
		default: return [];
	}
}
// content_end, text branch:
case "text":
	// Text was already streamed via content_start chunks; don't re-send.
	return [];
// content_end, tool branch:
case "tool": {
	const failed = !!e.error;
	return [{ sessionUpdate: "tool_call_update", toolCallId,
		status: failed ? "failed" : "completed",
		rawOutput: e.error ?? e.output }];
}
```

**Flow:** runtime event ⇒ translateEvent ⇒ content_start maps text→agent_message_chunk / reasoning→agent_thought_chunk / tool→tool_call(status "pending", rawInput) ⇒ content_end DROPS text and reasoning twins ("already streamed"), settles tools by `!!error`, and materializes media ONLY here: base64 image ⇒ image chunk, anything else ⇒ text degradation `[Generated {modality}: {mediaType}]` ⇒ each update sent fire-and-forget (`void`). done/error/iteration_*/usage produce NOTHING on this channel — fatal errors reach `prompt()` through the event-subscriber stash in acpAgent instead. `describeAgentError` = `getErrorMessage(error).trim() || "The agent reported an unknown error."`
**Invariant:** A tool_call emitted at start is ALWAYS settled by exactly one tool_call_update at end; text/reasoning payloads fly exactly once (at start); the runtime never awaits a client round-trip inside the event path; protocol errors are not reported as session updates.
**Probe:** `grep -cF 'void conn.sessionUpdate' apps/cli/src/acp/session-updates.ts` → 4; `grep -cF 'already streamed via content_start' apps/cli/src/acp/session-updates.ts` → 2; `grep -cF 'forwards generated images as ACP agent message chunks' apps/cli/src/acp/session-updates.test.ts` → 1. Direct suite `session-updates.test.ts` (1 case, read whole) pins ONLY the base64-image path — thin-suite caveat: the drop-text-at-end and tool-settlement invariants are source-read evidence.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "forwardAgentEvent translateEvent sessionUpdate content_start tool_call", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt payload-at-start/terminal-at-end streaming with fire-and-forget notification sends, one-shot text payloads, error-presence tool settlement, and end-only media materialization with graceful text degradation. Adapt the event-type names and update vocabulary to your protocol. Omit Cline's specific AgentEvent union. Coverage: source+test read whole at pin; MCP coverage check not runnable this session — recorded caveat.

