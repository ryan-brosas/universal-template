<!-- capsule-v2 -->
# Monotonic tool-call statuses + ordered emission — never downgrade, serialize updates

**Source:** pi-acp-jetbrain MIT `main@27aac05f`; Codebase Memory `pi-acp`. **Question:** How does the adapter track tool-call statuses across out-of-order pi events and guarantee `session/update` notifications are delivered in order?

## Monotonic tool statuses
**Path/Symbol:** `src/acp/session.ts:PiAcpSession` — `currentToolCalls` (316), `emit` (490-503), `flushEmits` (505-507), `handlePiEvent` `toolcall_*`/`tool_execution_start`/`tool_execution_update`/`tool_execution_end` (605-858).
**Signature:** `emit(update: SessionUpdate): void`; `private currentToolCalls = new Map<string, 'pending' | 'in_progress'>()`.
**Data Shape:** `currentToolCalls` maps `toolCallId → 'pending' | 'in_progress'`. `lastEmit: Promise<void>` is the serialization chain. `fileSnapshots`/`bashOutputSnapshots`/`fileMutationToolCallIds`/`bashToolCallIds` track per-tool state for diff/terminal rendering.

### Decisive source
```ts
private emit(update: SessionUpdate): void {
  // Serialize update delivery.
  this.lastEmit = this.lastEmit
    .then(() => this.conn.sessionUpdate({ sessionId: this.sessionId, update }))
    .catch(() => { /* Ignore notification errors; still want prompt completion */ })
}
```
```ts
// toolcall_delta: never downgrade an already-in_progress status
const existingStatus = this.currentToolCalls.get(toolCallId)
const status = existingStatus ?? 'pending'   // IMPORTANT: never downgrade
if (isBashTool(toolName)) {
  if (!existingStatus) this.currentToolCalls.set(toolCallId, 'pending')
  this.emitBashToolCall({ sessionUpdate: existingStatus ? 'tool_call_update' : 'tool_call', ..., status, includeTerminal: !existingStatus })
} else if (!existingStatus) {
  this.currentToolCalls.set(toolCallId, 'pending')
  this.emit({ sessionUpdate: 'tool_call', ..., status, rawInput })
} else {
  this.emit({ sessionUpdate: 'tool_call_update', status, rawInput })   // keep existing status
}
```
```ts
// tool_execution_start -> in_progress (transition, not downgrade)
this.currentToolCalls.set(toolCallId, 'in_progress')
```

**Flow:** A `toolcall_start`/`toolcall_delta`/`toolcall_end` event surfaces the tool call as `pending` (or keeps an existing `in_progress` status); `tool_execution_start` transitions it to `in_progress`; `tool_execution_update` streams partial output; `tool_execution_end` marks `completed`/`failed` and calls `cleanupToolCall`. Every `emit` is chained onto `lastEmit` so `session/update` notifications go out in order; `agent_settled`/prompt-failure paths call `flushEmits()` (await `lastEmit`) before resolving the prompt.

**Invariant:** Tool-call status is monotonic (`pending` → `in_progress` → `completed`/`failed`); a late `toolcall_delta` after execution started must not downgrade back to `pending` (clients hide progress on downgrade). All `session/update` notifications are serialized through the `lastEmit` promise chain.

**Probe:** `test/component/session-events.test.ts` ("PiAcpSession: emits tool_call + tool_call_update + completes", "PiAcpSession: preserves ordering when auto_retry_start is interleaved with text_delta events").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "currentToolCalls emit lastEmit tool_execution", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the monotonic status tracking and the promise-chain-ordered `session/update` emission. Adapt the specific pi event names and the ACP update shapes to the target agent/client. Omit the bash/terminal-specific emit helpers (covered by their own capsule) unless the target renders terminals.
