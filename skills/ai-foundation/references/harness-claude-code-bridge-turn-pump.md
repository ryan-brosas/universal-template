<!-- capsule-v2 -->
# Claude-code bridge turn pump — how do you drive an in-process agent SDK whose prompt channel is an async iterable you must implement yourself?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** When the runtime is an in-process SDK (`claude` Agent SDK `query()`) with no stdio protocol and no HTTP server — the bridge IS the process — how does the turn driver reconcile host steering, permissions, host tools, and terminal errors into one well-formed event stream?

## Async-iterable user-message pump with lifecycle reconciliation
**Path/Symbol:** `packages/harness-claude-code/src/bridge/index.ts` — `runTurn` (:250–505), `createQueryInput` (:507–630), `addUsage` (:632–659); runBridge entry (:128–135); permission plane `createPermissionOptions` (:139–212), `createPermissionSettings` (:214–238), `nativeToolRequiresApproval` (:240–248); host-tool MCP server construction (:266–307); query options (:339–390); terminal-error discipline (:393–407); result handling (:430–483).
**Signature:** `createQueryInput({ initialUserMessage, userMessages, abortSignal }): { input: AsyncIterable<unknown>; close(error?): void; handleLifecycle(message): void; hasActiveUserMessages(): boolean; observeResult(): void; hasObservedResult: boolean }`.
**Data Shape:** wire user message = `{type:'user', message:{role:'user', content:[{type:'text', text}]}, parent_tool_use_id:null, uuid, priority?}` — the initial prompt gets a randomUUID id and NO priority; steering messages carry their queue messageId as uuid plus `priority:'next'`. Lifecycle reconciliation keys on `command_uuid` matching a submitted messageId: states `queued|started` ⇒ `accept()`, `cancelled|discarded` ⇒ `reject(Error('Claude Code <state> the user message.'))`, then the entry is deleted either way.

### Decisive source
```ts
// index.ts:589–625 — the pump: initial prompt first, then queue items as they arrive
async next() {
  if (closed || abortSignal.aborted) return { value: undefined, done: true };
  if (!sentInitial) {
    sentInitial = true;
    return { value: toUserMessage({ text: initialUserMessage, messageId: randomUUID() }), done: false };
  }
  const nextMessage = await messageIterator.next();
  if (nextMessage.done) return { value: undefined, done: true };
  submittedMessages.set(nextMessage.value.messageId, nextMessage.value);
  return { value: toUserMessage({ text: nextMessage.value.text, messageId: nextMessage.value.messageId, priority: 'next' }), done: false };
}
// index.ts:566–575 — lifecycle reconciliation against what the runtime actually did
if (lifecycle.state === 'queued' || lifecycle.state === 'started') { submitted.accept(); return; }
if (lifecycle.state === 'cancelled' || lifecycle.state === 'discarded') {
  submitted.reject(new Error(`Claude Code ${lifecycle.state} the user message.`));
}
submittedMessages.delete(lifecycle.command_uuid);
```

**Flow:** runBridge hands the turn driver a StartMessage + BridgeTurn; the driver builds a local AbortController chained to `turn.abortSignal` (pre-aborted ⇒ abort immediately), creates the stream-event state, registers host tools as an IN-PROCESS McpServer named `harness-tools` (each tool's inputSchema converted via jsonSchemaToZodShape; execute emits `tool-call` providerExecuted:false → awaits `turn.requestToolResult` → emits `tool-result` → returns JSON text content), wires the compaction latch, and calls `claudeSdk.query({prompt: queryInput.input, options})`. The message loop breaks on abort, routes `command_lifecycle` to the pump, feeds everything to the emit translator, and on `result`/success accumulates usage (recursive addUsage: numbers add, objects recurse, else last-wins) + totalCostUsd, synthesizes structured_output as a text-start/delta/end triple forcing stepOpen, closes the step, observes the result, and closes+breaks ONLY when no active user messages remain. Terminal errors are latched once (emittedTerminalError) and close the pump + abort; a success result whose body is empty but where a terminal error was observed re-emits the error instead of finishing.
**Invariant:** steering stays exactly-once end-to-end — the host queue dedups by messageId while the pump reconciles each submission against the runtime's command_lifecycle (accept on queued/started, reject on cancelled/discarded), so a message the runtime dropped never silently vanishes; the query stays open past a result iff active user messages exist (submitted.size>0 || pendingCount>0); abort propagates BOTH ways (turn.abortSignal → local controller → pump close(reason) → queue close); usage on the final finish = accumulated result-usage (addUsage over every success result) falling back to step usage, never NaN.
**Probe:** `packages/harness-claude-code/src/bridge/index.test.ts` (301L, 6 cases): env merge (configured wins over inherited, unconfigured keys inherit); env omitted entirely when none configured; effort passthrough; responseFormat json+schema ⇒ outputFormat `{type:'json_schema', schema}`; final-step usage (finish-step[1].usage = LAST assistant message usage 20/3, finish.totalUsage = result usage 30/5 — earlier steps' usage excluded from the total); steering keeps the query open past the first result (acceptedUserMessages == ['steering-message-1'], two query inputs with the second carrying priority:'next' and the queue messageId as uuid).

## Permission plane as SDK options, not event answers
**Path/Symbol:** same file — `createPermissionOptions` (:139–212), `createPermissionSettings` (:214–238), `nativeToolRequiresApproval` (:240–248), NATIVE_TOOL_KINDS (:79–107); tool filtering `packages/harness-claude-code/src/bridge/tool-filtering.ts` whole 58L (`resolveNativeTools` :40–45, `resolveInactiveNativeTools` :47–57, PUBLIC_TO_NATIVE :5–32).
**Signature:** `createPermissionOptions({ start, inactiveNativeTools, turn, emit, finishApprovalStep, nativeToolCallNames, approvalRequestedToolUseIds }): Record<string, unknown>` (spread into query options).
**Data Shape:** fast path = `{permissionMode:'bypassPermissions', allowDangerouslySkipPermissions:true}` (NO canUseTool); slow path = `{permissionMode:'acceptEdits'|'default', allowDangerouslySkipPermissions:false, settings?:{permissions:{ask:[`${nativeName}(*)`…]}, sandbox:{autoAllowBashIfSandboxed:false}}, canUseTool}`. Kind table maps ~27 native names to readonly|edit|bash; unknown names default to 'edit' (fail-closed).

### Decisive source
```ts
// index.ts:154–159 — the bypass rung exists ONLY when nothing needs gating
if (permissionMode === 'allow-all' && inactiveNativeTools.size === 0) {
  return { permissionMode: 'bypassPermissions', allowDangerouslySkipPermissions: true };
}
// index.ts:171–209 — canUseTool ladder: auto-allow rungs, then announce + await host
if (toolName.startsWith('mcp__harness-tools__')) return { behavior: 'allow', updatedInput: toolInput };
if (!inactiveNativeTools.has(toolName) && !nativeToolRequiresApproval({ nativeName: toolName, permissionMode })) {
  return { behavior: 'allow', updatedInput: toolInput };
}
const approvalId = options.toolUseID;
input.approvalRequestedToolUseIds.add(approvalId);
input.nativeToolCallNames.set(approvalId, toolName);
input.emit({ type: 'tool-call', toolCallId: approvalId, toolName: toCommonName(toolName), nativeName: toolName, input: JSON.stringify(toolInput ?? {}), providerExecuted: true });
input.emit({ type: 'tool-approval-request', approvalId, toolCallId: approvalId });
input.finishApprovalStep(approvalId);
const decision = await input.turn.requestToolApproval(approvalId);
return decision.approved
  ? { behavior: 'allow', updatedInput: toolInput, toolUseID: approvalId }
  : { behavior: 'deny', message: decision.reason ?? 'Denied', toolUseID: approvalId };
```

**Flow:** builtinToolFiltering resolves to TWO lists — allowed native tools (mode 'allow' ⇒ the allowlist mapped through PUBLIC_TO_NATIVE; null/deny ⇒ undefined meaning "SDK default set") and inactive tools (allow-mode complement or deny-mode list) which ride `disallowedTools` so the model never sees them AND feed the ask-rules/settings gate. createPermissionSettings adds `${nativeName}(*)` ask rules for every inactive tool plus kind-gated tools (allow-reads gates edit+bash kinds, allow-edits gates bash only) and forces `sandbox.autoAllowBashIfSandboxed:false`; empty rule set ⇒ settings omitted. At call time canUseTool runs the ladder above; the approval path records the toolUseID in the translator state BEFORE emitting so the later assistant tool_use block for the same id is suppressed (no double tool-call), and the decision echoes toolUseID back so Claude ties the outcome to the right call.
**Invariant:** a gated native tool produces EXACTLY ONE tool-call (from canUseTool, not from the assistant block) and one tool-approval-request; denials carry the host reason verbatim (fallback 'Denied'); unknown native tool names are treated as 'edit' kind so new Claude builtins fail closed under allow-reads/allow-edits; the bypass rung is unreachable whenever any tool is inactive, so filtered tools can never execute unapproved even in allow-all.
**Probe:** `tool-filtering.test.ts` (42L, 6 cases): undefined without filtering; allowlist common→native mapping (read⇒Read etc.); empty allowlist preserved (all inactive); deny mode ⇒ resolveNativeTools undefined but inactive list populated; native-only names preserved unmapped. Permission-ladder wiring itself is deterministic-read-only (index.test.ts mocks requestToolApproval but never drives a gated call) — recorded as coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createQueryInput handleLifecycle command_lifecycle createPermissionOptions canUseTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the async-iterable-pump shape for any in-process SDK whose prompt channel is a pull-based iterator: yield the initial message first, tag steering with its stable id + priority, and reconcile submissions against runtime lifecycle events (accept/reject by observed state) instead of trusting fire-and-forget delivery; adopt the three-rung permission-options split (full bypass only when nothing is gated / mode mapping + per-call callback / settings ask-rules as defense-in-depth) and the echo-the-id-back denial shape; adopt recursive addUsage (numbers add, objects recurse, else last-wins) for accumulating per-result usage into one total; adapt the kind table and name maps to your runtime's builtins; omit the pump entirely when the runtime already owns its input channel (ACP stdio, opencode HTTP). Bridge-side twin of the pass-23 host-side hello-ladder capsule (harness-claude-code-websocket-hello-ladder.md covers the HOST opening this socket; this capsule covers the sandbox side behind it); the emit translator around the pass-25 compaction latch is documented in harness-claude-code-bridge-emit-translator.md. Caveat: the permission ladder and continue-rule wiring are deterministic-read-only; the pump, env/options plumbing, usage accumulation, and steering are test-pinned.
