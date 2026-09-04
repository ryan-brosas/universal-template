<!-- capsule-v2 -->
# Mutation-output suppression — when a tool call will render as a diff, its stream stays empty

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** When a tool call will be rendered as a structured diff, what must its streaming updates suppress — and why are diff and rawOutput mutually exclusive?

## tool_execution_update/end suppression for edit/write
**Path/Symbol:** `src/acp/session.ts` `handlePiEvent` `tool_execution_update` (:826-848) and `tool_execution_end` (:850-906) — the `fileMutationToolCallIds` branches.
**Signature:** none (branch contract inside `handlePiEvent`).
**Data Shape:** `fileMutationToolCallIds: Set<toolCallId>` (populated at `tool_execution_start` for `edit`/`write`, owned by structured-edit-diff.md); update events carry `partialResult`; end events carry `result` + `isError`.

### Decisive source
```ts
case 'tool_execution_update': {
  ...
  const text = this.fileMutationToolCallIds.has(toolCallId) ? '' : toolResultToText(partial)
  this.emit({
    sessionUpdate: 'tool_call_update',
    toolCallId,
    status: 'in_progress',
    content: text ? ([{ type: 'content', content: { type: 'text', text } }]) : undefined,
    ...(this.fileMutationToolCallIds.has(toolCallId) ? {} : { rawOutput: partial })
  })
  break
}
```
```ts
// tool_execution_end: diff emission and rawOutput are mutually exclusive
this.emit({
  sessionUpdate: 'tool_call_update',
  toolCallId,
  status: isError ? 'failed' : 'completed',
  content,                                              // [{type:'diff',...}] when the file changed
  ...(hasStructuredDiff ? {} : { rawOutput: result })   // raw output ONLY when no diff was emitted
})
```

**Flow:** at every streaming update for a file-mutation tool call, the adapter emits a bare status transition — no text content, no rawOutput — because the client will render the realized change as a structured `diff` at completion (snapshot vs re-read, owned by structured-edit-diff.md). Non-mutation tool calls stream `toolResultToText(partial)` as text content plus the raw payload. At end, if a structured diff was emitted, `rawOutput` is omitted; otherwise the raw result rides `rawOutput`. Failed mutations (`isError`) skip the diff and surface the raw result instead.
**Invariant:** a tool call renders through exactly ONE payload channel — structured diff OR raw output, never both; streaming updates for diff-bound calls carry no partial payload (a partial file state is meaningless to the client and would fight the final diff); the suppression set is keyed by toolCallId and cleaned up by `cleanupToolCall` (:588-594) so the next call to the same file starts fresh.
**Probe:** `test/component/session-diff.test.ts` — "expected raw output to be suppressed when diff is emitted" assertions at :64 and :180 (end events for edit and write both pin `rawOutput === undefined` when the diff content is present); `test/component/session-events.test.ts` "emits tool_call + tool_call_update + completes" (:74-129 — bash tool call streaming path, the non-mutation contrast: terminal `_meta` output instead of rawOutput). The in-flight update suppression branch (:836-846) is source-read at this pin — no direct test streams a mid-mutation `tool_execution_update` — recorded as a coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "fileMutationToolCallIds tool_execution_update rawOutput hasStructuredDiff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-payload-channel-per-call: suppress streaming payloads for diff-bound mutations and make diff-vs-rawOutput exclusive at completion. Adapt the trigger set (edit/write) to your agent's mutation tools. Omit the failed-mutation raw passthrough only if your client renders errors from the diff channel.
