<!-- capsule-v2 -->
# acp-session-replay-hygiene — how do you replay a persisted conversation to a client without leaking runtime markup or breaking tool-call pairing?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What must be stripped, awaited, or re-paired when a stored transcript is projected onto a protocol client?

## Awaited in-order replay; display-projection first; strip user wrappers, replay assistant verbatim; tool_use replays pending until its tool_result settles it
**Path/Symbol:** `apps/cli/src/acp/session-load.ts` (`replaySessionHistory` :26-33, `translateHistoricalMessage` :35-39, `translateProjectedHistoricalMessage` :41-152, `isSyntheticUserText` :19-21, `flattenToolResultContent` :154-183).
**Signature:** `replaySessionHistory(conn: AgentSideConnection, sessionId: string, messages: MessageWithMetadata[]): Promise<void>` — awaits EVERY notification before resolving.
**Data Shape:** In: persisted `MessageWithMetadata[]` (role + string-or-block content + optional `metadata.modelToolActivities`). Out: ordered `user_message_chunk` / `agent_message_chunk` / `agent_thought_chunk` / `tool_call` / `tool_call_update` notifications.

### Decisive source
```ts
// The ACP spec requires the entire conversation to be replayed via
// session/update notifications before this request resolves.
for (const message of messages) {
	for (const update of translateHistoricalMessage(message)) {
		await conn.sessionUpdate({ sessionId, update });
	}
}
// user text boundary:
const text = formatDisplayUserInput(block.text);   // strips <user_input mode> + <mode_notice>;
	if (!text || isSyntheticUserText(text)) break;  // formats <user_command slash> to /cmd
// assistant text replays VERBATIM — even when it QUOTES the literal wrapper.
// provider-executed tools ride metadata.modelToolActivities and are emitted
// as a pending tool_call + completed tool_call_update BEFORE the text chunk.
```

**Flow:** messages ⇒ `projectSessionMessagesForDisplay` (core display projection) ⇒ per block: user text → formatDisplayUserInput, drop empty and the synthetic act-mode continuation prompt (mirrors tui/utils/hydrate-messages.ts); assistant text → verbatim agent chunk; thinking → agent_thought_chunk; image/media → role-routed image chunk or `[Generated …]` degradation; tool_use → tool_call(pending); tool_result → tool_call_update(status by `is_error`, rawOutput = flattenToolResultContent: text/file verbatim, image→"[image]", default JSON.stringify with String() fallback, "\n"-joined).
**Invariant:** Replay order equals persistence order and every notification is awaited (spec: the whole conversation must be replayed before session/load resolves); user text never carries runtime markup to the client; assistant text is never rewritten; every historical tool_call is settled by its paired tool_call_update.
**Probe:** `grep -cF 'await conn.sessionUpdate' apps/cli/src/acp/session-load.ts` → 1; `grep -cF 'isSyntheticUserText' apps/cli/src/acp/session-load.ts` → 2; `grep -cF 'does not replay the synthetic act-mode continuation prompt' apps/cli/src/acp/session-load.test.ts` → 1; `grep -cF 'sends one awaited notification per update, in order' apps/cli/src/acp/session-load.test.ts` → 1. Direct suite `session-load.test.ts` (12 cases, read whole) pins wrapper-strip, mode-notice strip, slash-command formatting, synthetic-prompt drop, assistant-verbatim quoting, modelToolActivities ordering, and native-result JSON.stringify.

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "replaySessionHistory translateHistoricalMessage formatDisplayUserInput modelToolActivities", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt awaited in-order replay, display-projection-before-transport, asymmetric user-strip/assistant-verbatim text handling, synthetic-prompt filtering, and pending-then-settled historical tool pairing. Adapt the wrapper vocabulary (`<user_input>`, `<mode_notice>`, `<user_command>`) and the display projection to your transcript format. Omit Cline's provider metadata specifics. Coverage: source+test read whole at pin; MCP coverage check not runnable this session — recorded caveat.

