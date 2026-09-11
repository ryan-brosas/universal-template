<!-- capsule-v2 -->
# Turn state machine — an ACP prompt completes only on agent_settled

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d` (drift-repinned from `27aac05f`, pass 3); Codebase Memory `pi-acp`. **Question:** How does a single ACP `session/prompt` map to pi's multi-event turn lifecycle (retry, compaction, queued continuations) without resolving too early — and how must child death and dispose settle the pending turn?

## Turn state machine
**Path/Symbol:** `src/acp/session.ts:PiAcpSession.prompt` (424-460), `startTurn` (563-603), `handlePiEvent` `agent_start`/`turn_end`/`agent_end`/`agent_settled` (910-953).
**Signature:** `prompt(message: string, images?: unknown[]): Promise<StopReason>`.
**Data Shape:** `pendingTurn: PendingTurn | null` (one in-flight turn), `turnQueue: QueuedTurn[]` (additional prompts), `cancelRequested: boolean`. `inAgentLoop` was REMOVED upstream (dead state — `agent_settled` alone completes). `StopReason = 'end_turn' | 'cancelled' | 'error'`.

### Decisive source
```ts
// handlePiEvent
case 'turn_end':   // sub-step (e.g. tool_use); pi will start another turn. Do NOT resolve.
  break
case 'agent_end':  // one low-level run ended; pi may still retry/compact/continue.
  this.inAgentLoop = false
  break
case 'agent_settled':  // THE completion signal
  void this.flushEmits().finally(() => {
    const reason: StopReason = this.cancelRequested ? 'cancelled' : 'end_turn'
    this.pendingTurn?.resolve(reason)
    this.pendingTurn = null
    this.inAgentLoop = false
    const next = this.turnQueue.shift()
    if (next) { this.emit({ sessionUpdate:'agent_message_chunk', content:{type:'text', text:`Starting queued message.`} }); this.startTurn(next) }
    else this.emit({ sessionUpdate:'session_info_update', _meta:{ piAcp:{ queueDepth:0, running:false } } })
  })
  break
```
```ts
// prompt(): if a turn is already running, enqueue
if (this.pendingTurn) { this.turnQueue.push(queued); this.emit(...'Queued message (position N)'); return }
this.startTurn(queued)
```
```ts
// agent.ts prompt() maps result -> ACP StopReason
const stopReason: StopReason = result === 'error' ? (session.wasCancelRequested() ? 'cancelled' : 'end_turn') : result
```

**Flow:** `prompt` expands slash commands, then starts a turn (or enqueues). `startTurn` resets `cancelRequested=false`, sets `pendingTurn`, emits queue-depth metadata, and calls `proc.prompt(...)` — but completion is NOT tied to the RPC response (it only acknowledges acceptance). Pi may emit multiple `agent_end` events (retry, compaction, queued continuation); the ACP prompt resolves only on `agent_settled`, after flushing all enqueued `session/update` notifications. `cancel()` sets `cancelRequested`, resolves queued turns as `cancelled`, aborts the pi subprocess, and cancels bridge tool calls.

**Invariant:** `turn_end` and `agent_end` must never resolve the ACP prompt; only `agent_settled` does. A `cancelRequested` flag flips the final stopReason to `cancelled`. Queued prompts start only after `agent_settled` flushes. DRIFT ADDENDUM (pass 3, `1f0524f`): child-process exit and `dispose()` now ALSO settle the pending turn (`handleProcessExit` resolves `'cancelled'|'error'` with `lastError` = message + 8-line stderr tail; dispose settles in-flight as `'cancelled'` after flushEmits) — a pending turn has exactly one winning settlement because each path nulls `pendingTurn` before resolving. Error results now carry `_meta.piAcp.error` instead of silently mapping to end_turn (see turn-settling-hardening.md).

**Probe:** `test/component/session-events.test.ts` ("PiAcpSession: prompt stays open through retry runs until agent_settled", "PiAcpSession: queues concurrent prompt and starts it after agent_settled", "PiAcpSession: cancel flips stopReason to cancelled", "PiAcpSession: cancel clears queued prompts").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-acp", query: "agent_settled pendingTurn turnQueue", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the `agent_settled`-driven completion, the pending-turn + queue model, and the `cancelRequested` → `cancelled` stopReason mapping. Adapt the specific pi event names to the target agent's RPC protocol. Omit the `flushEmits`/queue-depth metadata details unless the target client renders them.
