<!-- capsule-v2 -->
# Streaming tool-call input assembly — surface the call before its arguments exist

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** How do you surface a streaming tool call to the client BEFORE its arguments are complete — including malformed partial JSON?

## toolcall_* → immediate tool_call with a three-rung rawInput ladder
**Path/Symbol:** `src/acp/session.ts` `handlePiEvent` `message_update` toolcall branch (:677-744) + `toToolKind` (:1207-1219).
**Signature:** `function toToolKind(toolName: string): ToolKind`.
**Data Shape:** pi's `assistantMessageEvent` of type `toolcall_start|toolcall_delta|toolcall_end` carries either `event.toolCall` directly or the partial assistant message at `event.partial.content[event.contentIndex]`; the tool call has `{id, name, arguments?}` and possibly `partialArgs: string`.

### Decisive source
```ts
// Surface tool calls ASAP so clients (e.g. Zed) can show a tool-in-use/loading UI
// while the model is still streaming tool call args.
if (ame?.type === 'toolcall_start' || ame?.type === 'toolcall_delta' || ame?.type === 'toolcall_end') {
  const toolCall = (ame as any)?.toolCall
    ?? (ame as any)?.partial?.content?.[(ame as any)?.contentIndex ?? 0]
  const rawInput =
    (toolCall as any)?.arguments && typeof (toolCall as any).arguments === 'object'
      ? (toolCall as any).arguments                      // rung 1: complete args object
      : (() => {
          const s = String((toolCall as any)?.partialArgs ?? '')
          if (!s) return undefined                       // rung 0: nothing streamed yet
          try { return JSON.parse(s) }                   // rung 2: partial JSON that still parses
          catch { return { partialArgs: s } }            // rung 3: malformed partial -> visible wrapper
        })()
  ...
  this.emit({ sessionUpdate: 'tool_call', toolCallId, title: toolName,
              kind: toToolKind(toolName), status, locations, rawInput })
}
```
```ts
function toToolKind(toolName: string): ToolKind {
  switch (toolName) {
    case 'read': return 'read'
    case 'write': case 'edit': return 'edit'
    case 'bash': return 'execute'   // bash actually diverts to emitBashToolCall, also kind 'execute'
    default: return 'other'
  }
}
```

**Flow:** every `toolcall_*` delta re-derives rawInput from the latest snapshot and emits a `tool_call` (first sight) or `tool_call_update` (subsequent) through the ordered emit chain — the client watches arguments grow in real time. Status handling (`existingStatus ?? 'pending'`, never downgrade) is owned by monotonic-tool-statuses.md; bash routing (`isBashTool` → `emitBashToolCall` with terminal content) by bash-terminal-rendering.md; location extraction by structured-edit-diff.md. This capsule owns the INPUT-ASSEMBLY ladder and the kind mapping.
**Invariant:** the tool call is surfaced on the FIRST delta, not at execution start — latency of client UI beats argument completeness; malformed partial JSON is never dropped silently (rung 3 wraps it as `{partialArgs: s}` so the client can render what arrived); the ladder is total (undefined is the explicit "nothing yet" answer); `toToolKind` is a closed map with `other` as the safe default.
**Probe:** `test/component/session-events.test.ts` "PiAcpSession: emits tool locations from pi path args" (toolcall_start with `arguments: {path, content}` → `locations: [{path: '/tmp/test.txt'}]`); the rawInput rungs themselves are source-read at this pin (no direct test streams partialArgs shapes through FakePiRpcProcess) — recorded as a coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "toolcall_start partialArgs rawInput toToolKind contentIndex", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt first-delta surfacing with the four-rung input ladder (none → object → parseable → wrapped) and the closed kind map. Adapt the event field names to your model's streaming shape. Omit the malformed-JSON wrapper only if your client tolerates missing rawInput until execution start.
