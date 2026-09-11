<!-- capsule-v2 -->
# session/load history replay — how do you project stored agent history into ACP chunks and synthetic tool calls?

**Source:** pi-acp-jetbrain MIT `main@1f0524f777c93c51747c26d24f3609c2a4e6731d`; Codebase Memory `pi-acp`. **Question:** When a client restores a previous conversation, how must each stored message role be projected onto `session/update` notifications so the transcript renders faithfully — including historic tool executions?

## Replay driver in loadSession
**Path/Symbol:** `src/acp/agent.ts:PiAcpAgent.loadSession` (:1359-1556) — teardown+lookup (:1364-1391), replay loop (:1393-1488), restored bridge info gate (:1490-1506), post-response advertisement (:1519-1553).
**Signature:** `loadSession(params: LoadSessionRequest): Promise<LoadSessionResponse>`.
**Data Shape:** pi `getMessages()` → `{messages[]}` with role ∈ user|assistant|toolResult; toolResult carries `toolCallId`, `toolName`, `isError`. Emission pairs: `tool_call` then `tool_call_update` sharing one `toolCallId`.

### Decisive source
```ts
// If the client is re-loading a session that is already active, tear down the existing
// pi subprocess so we can start fresh and re-advertise commands reliably.
await this.closeManagedSession(params.sessionId)
const stored = this.findStoredSession(params.sessionId)
if (!stored) throw RequestError.invalidParams(`Unknown sessionId: ${params.sessionId}`)
...
for (const m of messages) {
  const role = String(m?.role ?? '')
  if (role === 'user')      { /* normalizePiMessageText -> user_message_chunk (skip empty) */ }
  if (role === 'assistant') { /* normalizePiAssistantText -> agent_message_chunk */ }
  if (role === 'toolResult') {
    const isBash = isBashTool(toolName)
    if (isBash) {
      await this.conn.sessionUpdate({ sessionId, update: { sessionUpdate: 'tool_call',
        toolCallId, title: bashCommand(m) ?? toolName, kind: 'execute', status: 'completed',
        content: bashTerminalContent(toolCallId),
        _meta: bashTerminalInfoMeta(toolCallId, params.cwd) } })
      await this.conn.sessionUpdate({ sessionId, update: { sessionUpdate: 'tool_call_update',
        toolCallId, status: isError ? 'failed' : 'completed',
        _meta: { ...(text ? bashTerminalOutputMeta(toolCallId, text) : {}),
                 ...bashTerminalExitMeta(toolCallId, bashExitCode(m, isError)) } } })
      continue
    }
    // Create a synthetic ACP tool call to render historic tool usage.
    await this.conn.sessionUpdate({ sessionId, update: { sessionUpdate: 'tool_call',
      toolCallId, title: toolName,
      kind: toolName === 'read' ? 'read' : toolName === 'write' || toolName === 'edit' ? 'edit' : 'other',
      status: 'completed', rawInput: null, rawOutput: m } })
    const text = toolResultToText(m)
    await this.conn.sessionUpdate({ sessionId, update: { sessionUpdate: 'tool_call_update',
      toolCallId, status: isError ? 'failed' : 'completed',
      content: text ? [{ type: 'content', content: { type: 'text', text } }] : null, rawOutput: m } })
  }
}
```
```ts
// Restored bridge info survives quietStartup only when high-signal:
const restoredStartupInfo = restoredBridgeInfo &&
  (!getQuietStartup(params.cwd) || Boolean(bridgeStatus?.diagnostics.length) ||
   Boolean(bridgeStatus?.failed) || !bridgeStatus?.catalogComplete ||
   bridgeStatus?.lifecycle !== 'ready') ? restoredBridgeInfo : null
```

**Flow:** absolute-cwd guard → tear down an ACTIVE same-id subprocess (fresh re-advertisement on client re-load) → unknown store id ⇒ invalidParams → restoreSession (spawns fresh bound to stored file) → single-live-subprocess sweep → store upsert refresh → getMessages → ordered role dispatch (user chunk / assistant chunk / synthetic tool pair; bash gets full terminal rendering with cwd-anchored info meta, others get kind-mapped generic calls with flattened text) → config options → conditional restored-startup-info (quiet mode keeps only diagnostics/failures/incomplete catalogs) → response, THEN startup delivery + command advertisement deferred one macrotask.
**Invariant:** Replay is strictly sequential (`await` per update) preserving transcript order; every synthetic tool call is completed or failed — never left pending; empty normalized texts are skipped rather than emitted as blank chunks; the response precedes any notification for the new sessionId.
**Probe:** `test/component/session-load-toolresult.test.ts` ("loadSession replays toolResult as tool_call + tool_call_update" pins bash title `'echo hello'`, `kind:'execute'`, terminal content + `_meta.terminal_info{terminal_id,cwd}`, `_meta.terminal_output.data='hello from bash'`, `_meta.terminal_exit{exit_code:0}`); also `test/unit/startup-info-load-session.test.ts` ("does not emit startup info on loadSession" quiet path).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.trace_path({ project: "pi-acp", function_name: "pi-acp.src.acp.agent.PiAcpAgent.loadSession", direction: "outbound", depth: 2 });
// -> callees_total 40: whole translate layer (bashCommand/bashTerminal*Meta/isBashTool/toolResultToText/
//    normalizePi*Text), toAvailableCommandsFromPiGetCommands, mergeCommands, getSessionConfiguration ...
```

## Verdict
Adopt role-dispatched replay with synthetic completed/failed tool-call pairs, bash-specific terminal projection, strict sequencing, and respond-before-notifying ordering. Adapt the kind mapping and quiet-mode exceptions to your client's renderer. Omit nothing else — this driver composes capsules already mined (normalizers, bash metas, result flattener). Coverage: all cited paths `no_recorded_issue`.
