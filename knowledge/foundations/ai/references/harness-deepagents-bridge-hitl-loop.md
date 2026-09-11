<!-- capsule-v2 -->
# Deep Agents bridge HITL loop — how do you drive a LangGraph agent whose human-in-the-loop pauses arrive as state interrupts, not stream events?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** Deep Agents (LangGraph) pauses a gated tool call by ENDING the stream with an interrupt recorded in graph state — there is no permission event on the wire. How does the bridge turn that into the harness approval protocol and resume the same graph without losing the step/usage/tool-call structure?

## One agent per process, reused across turns
**Path/Symbol:** `packages/harness-deepagents/src/bridge/index.ts` — module state (:129–134), `buildModel` (:53–82), `createReasoningMiddleware` (:84–118), `responseFormatMiddleware` (:147–157), `buildHostTools` (:160–184), `runTurn` (:186–383) with agent construction (:199–253), stream config (:268–275), `readPendingApprovals` (:278–289), HITL loop (:296–370), terminal finish (:372–382); `loadMcpTools` (:396–415), `closeMcpClient` (:417–422); translator correlation in `create-emit-stream-event.ts` — `on_tool_start` (:176–202), `on_tool_end` (:203–222), `flushStep` (:253–270).
**Signature:** `runTurn(start: StartMessage, turn: BridgeTurn): Promise<void>`; resume input type `unknown | Command<{resume: {decisions: Array<{type:'approve'}|{type:'reject', message?}>}}>`.
**Data Shape:** agent built ONCE per bridge process (module-level `agent`, `currentTurn`, `mcpClient`, `mcpToolNames`, `currentResponseFormat`) with `checkpointer: new MemorySaver()` (a real instance — LangGraph rejects `true` for root graphs) giving multi-turn memory; tools = external MCP tools (MultiServerMCPClient with `prefixToolNameWithServerName:true` + `additionalToolNamePrefix:'mcp'`, host-name collisions filtered out) + host tools (LangChain `tool()` wrappers that emit `tool-call` providerExecuted:false → await `turn.requestToolResult` → return stringified output, toolCallId = `${name}-${uuid}`); backend = `createLocalShellBackend({rootDir: workdir})`; systemPrompt rides `{suffix: instructions}`; middleware order = responseFormat → reasoning? → builtinFiltering?.

### Decisive source
```ts
// index.ts:296–370 (abridged) — the while(true) interrupt loop
while (true) {
  const stream = await agent.streamEvents(resumeInput as never, config);
  for await (const event of stream) { emitStreamEvent(event); /* structuredResponse capture */ }
  const actionRequests = await readPendingApprovals();
  if (actionRequests.length === 0) break;
  const decisions = [];
  for (const action of actionRequests) {
    const approvalId = `approval-${randomUUID()}`;
    endTextBlock(...); endReasoningBlock(...);
    emit({ type: 'tool-call', toolCallId: approvalId, toolName: toCommonName(action.name), input: JSON.stringify(action.args ?? {}), providerExecuted: true, nativeName: action.name });
    emit({ type: 'tool-approval-request', approvalId, toolCallId: approvalId });
    flushStep({ state: streamEventState, emit });
    const decision = await turn.requestToolApproval(approvalId);
    if (decision.approved) {
      const queue = streamEventState.approvedToolQueue.get(action.name) ?? [];
      queue.push(approvalId); streamEventState.approvedToolQueue.set(action.name, queue);
      decisions.push({ type: 'approve' });
    } else {
      emit({ type: 'tool-result', toolCallId: approvalId, toolName: toCommonName(action.name), result: decision.reason ?? 'Rejected by user.' });
      decisions.push({ type: 'reject', ...(decision.reason ? { message: decision.reason } : {}) });
    }
  }
  resumeInput = new Command({ resume: { decisions } });
}
```

**Flow:** each turn sets currentTurn + currentResponseFormat (toolStrategy(schema) when responseFormat json+schema), builds interruptOn from (permissionMode, builtinToolFiltering), constructs the agent only on the first turn, then loops: streamEvents(resumeInput) with config `{version:'v2', configurable:{thread_id:'bridge-session'}, recursionLimit?, signal: turn.abortSignal}`; every event feeds the translator (which drops nested subagent events via the `|`-delimited checkpoint namespace, counts nested usage toward totals but bounds visible steps to top-level calls, buffers the step at model-end and flushes it when the NEXT model call starts or the turn ends); structured output is captured once from the root-namespace `on_chain_end` carrying `output.structuredResponse` and emitted as a text triple. After each stream segment, readPendingApprovals reads `agent.getState().tasks[].interrupts[]` flattened by collectActionRequests (missing args default to `{}`); zero requests ⇒ break; otherwise each gated call is announced (blocks closed first, then tool-call + tool-approval-request + flushStep so the approval lands in its own finished step), the host decision is awaited, approved ids are queued per tool NAME in approvedToolQueue (the translator's on_tool_start shifts the matching id out of the queue and records approvedRunIds[runId]=approvalId so the later on_tool_end reuses the APPROVAL id as toolCallId — the call is announced exactly once, at approval time), rejected calls emit their tool-result immediately (they will never execute) plus a reject decision; the loop resumes with `new Command({resume:{decisions}})`. Terminal: close blocks, flushStep, emit finish with accumulated inputTokens/outputTokens totals.
**Invariant:** a gated builtin produces EXACTLY ONE tool-call (at approval time, not at execution time) and its tool-result reuses the approval id, so consumers see one coherent call/result pair across the pause; rejections surface a result NOW with the host reason (fallback 'Rejected by user.') instead of dangling; the loop terminates because either no interrupts remain or the host aborts (signal rides the stream config); the agent/checkpointer persist across turns in-process (thread_id constant 'bridge-session') so multi-turn memory is free, but cross-process resume is impossible — this dialect has no replay story (contrast ACP disk-replay and cline parked sessions); MCP tool names are prefixed `mcp__<server>__<tool>` and host tools win name collisions (external tools with a host name are dropped).
**Probe:** `packages/harness-deepagents/src/bridge/index.test.ts` (190L, 3 cases): instructions appended as systemPrompt suffix; reasoning configured on the DEFAULT Deep Agents model (no host model ⇒ createReasoningMiddleware path with thinking+effort); requested JSON schema applied for the active turn (responseFormat middleware sees toolStrategy output). `approvals.test.ts` (151L, 14 cases): allow-all never gates; allow-edits gates only bash kind; allow-reads gates edit+bash; undefined when nothing gated; inactive builtins excluded from gating (filtering policy alone never adds gates); native-name mapping for allow/deny policies; collectActionRequests flattening across interrupts with missing-args default + ignore-no-action-requests. `local-shell-backend.test.ts` (54L, 2 cases): only PATH crosses into shell env; fallback PATH when absent. `tool-filtering.test.ts` (252L, 5 cases): inactive builtins denied while custom calls stay pending; jumpTo:'model' only when EVERY call denied; deny policy on native names without blocking active builtins; native-only builtin denial; no-op when all active. `create-emit-stream-event.test.ts` (278L, 5 cases): model/content/step events with nested usage counting; tool-input unwrapping (`{input:'<json>'}` single-key unwrap) + approved call id reuse; reasoning from Anthropic + normalized LangChain blocks; only external MCP marked dynamic; internal StructuredOutput tool suppressed.

## Gating config + filtering middleware
**Path/Symbol:** `packages/harness-deepagents/src/bridge/approvals.ts` whole 92L — NATIVE_TOOL_KIND (:6–18), `toCommonName` (:27–29), `isBuiltinToolIncluded` (:31–40), `builtinToolRequiresApproval` (:42–49), `buildInterruptOn` (:52–75), `collectActionRequests` (:81–92); `tool-filtering.ts` whole 129L — `createBuiltinToolFilteringMiddleware` (:56–129); `local-shell-backend.ts` whole 19L — `SANDBOX_PATH_FALLBACK` (:3–4), `createLocalShellBackend` (:6–19).
**Signature:** `buildInterruptOn(permissionMode, builtinToolFiltering): Record<string, {allowedDecisions: ['approve','reject']}> | undefined`.
**Data Shape:** kind table maps 9 native names (read_file/write_file/edit_file/execute/grep/glob/ls/task/write_todos) to readonly|edit|bash; interruptOn entries carry `allowedDecisions:['approve','reject']` per gated native name; the middleware is a plain object branded `Symbol.for('AgentMiddleware')` with an afterModel hook (`canJumpTo:['model']`).

### Decisive source
```ts
// tool-filtering.ts:67–125 (abridged) — afterModel denies inactive builtins IN STATE
hook: (state) => {
  const lastMessage = [...state.messages].reverse().find(m => AIMessage.isInstance(m));
  if (!lastMessage?.tool_calls?.length) return undefined;
  let hasActiveToolCalls = false;
  const deniedToolMessages: ToolMessage[] = [];
  for (const toolCall of lastMessage.tool_calls) {
    if (!isInactiveBuiltinToolCall({ toolCall, builtinToolFiltering })) { hasActiveToolCalls = true; continue; }
    toolCall.id ??= `${nativeName}-filtered-${deniedToolMessages.length}`;
    emit({ type: 'tool-call', ... providerExecuted: true, nativeName });
    emit({ type: 'tool-result', ... result: reason });
    deniedToolMessages.push(new ToolMessage({ content: reason, name: nativeName, tool_call_id: toolCall.id, status: 'error' }));
  }
  if (deniedToolMessages.length === 0) return undefined;
  return { messages: [lastMessage, ...deniedToolMessages], ...(hasActiveToolCalls ? {} : { jumpTo: 'model' }) };
}
```

**Flow:** buildInterruptOn gates ONLY builtins that are both included by the filtering policy AND require approval under the mode (allow-all ⇒ none; allow-edits ⇒ bash kind; allow-reads ⇒ edit+bash kinds) — host tools approve at the agent layer (requestToolResult), never here. When the model still calls a filtered-out builtin, the middleware intercepts AFTER the model: it emits the tool-call + a synthetic error-status ToolMessage (reason naming the HarnessAgent filtering policy) into the graph STATE, and jumps back to the model only when every call was denied (active siblings must still execute first). LocalShellBackend receives PATH-only env (fallback `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`) so no secrets cross into shell commands.
**Invariant:** filtering and approval are orthogonal axes — a tool can be inactive (middleware-denied, never executed, model told why) or active-but-gated (HITL-paused, host decides); the middleware never invents ids for calls that already have one (`??=` minting) and never jumps when any active call remains, so mixed batches keep executing; denied results ride status:'error' ToolMessages so the model sees a real failure, not silence.
**Probe:** approvals.test.ts (14 cases) + tool-filtering.test.ts (5 cases) + local-shell-backend.test.ts (2 cases) as enumerated above — all three kernels fully test-pinned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "buildInterruptOn collectActionRequests readPendingApprovals approvedToolQueue createBuiltinToolFilteringMiddleware", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the while(true) stream→state→decide→Command-resume loop for any graph runtime whose HITL mechanism is state interrupts rather than wire events: read pending actions from graph state AFTER each stream segment, announce-then-await per action, resume with a decision array, and break on empty; adopt the announce-at-approval-time + id-reuse-at-execution pattern (per-name queue + runId→approvalId map) so paused calls stay single-identity across the pause; adopt rejected-emits-result-now (rejected work never executes, so the outcome must surface immediately); adopt the afterModel deny-in-state middleware with conditional jumpTo for tool visibility filtering in graph runtimes; adopt PATH-only shell env for any in-sandbox shell backend; adapt the kind table/name maps to your runtime's builtins; omit the whole plane where the runtime emits permission events natively (ACP/opencode/claude-code bridges). Pairs with harness-dialect-wireturn-invariant-core.md (host-side twin) and harness-deepagents-instructions-once.md (attach semantics). Caveat: the HITL loop wiring (index.ts :296–370) is deterministic-read-only — index.test.ts mocks streamEvents/getState but never drives an interrupt round-trip; the kernels it feeds (approvals, filtering, backend, translator) are fully test-pinned.
