<!-- capsule-v2 -->
# Client-tool round-trip protocol — browser-executed agent tools that are ACKed before any work, so results must come back as conversation messages

**Source:** OpenHands / All-Hands-AI MIT `main@8511fff62d3084587cda1add483fe5ea9c8bfd7e`; Codebase Memory `openhands`. **Question:** How does a web UI execute a tool call the agent made against *it* (not the server), return a result to the agent, and survive event-stream replays without launching twice?

## Connected graph-selected seam
**Path/Symbol:** `src/services/child-conversation-launch.ts:handleLaunchChildConversationAction` (505–536) ← dispatched by `src/context*s/conversation-websocket-context.tsx` `ConversationWebSocketProvider` and `WebSocketProviderWrapper` (trace_path inbound depth 4, executed this pass). Siblings: `claimToolCall` (205–227), `validateLaunchParams` (110–194), `launchLocalChild` (272–350), `waitForCloudConversationId` (365–384), `reportLaunchResult` (459–497); spec `src/api/launch-child-conversation-client-tool.ts` (`ClientToolSpec`, annotations) and `src/api/canvas-ui-client-tool.ts:9–20`; discriminators `src/constants/child-conversation.ts` (`ClientAction_<tool-name>` SDK convention at :8–9, `CHILD_CONVERSATION_RESULT_PREFIX = "[child-conversation] "` at :20, `MIN_AGENT_SERVER_VERSION_FOR_PARENT_LINK = "1.37.1"` at :37). Direct test: `__tests__/services/child-conversation-launch.test.ts` (565 L; 20 cases incl. replay-ignore :490, goal-loop skip :510, shared fallback :324/:360).
**Signature:** `handleLaunchChildConversationAction(action, parentConversationId, toolCallId): Promise<void>` — **never rejects**; `ClientToolSpec { name, description, parameters, annotations?: { title?, readOnlyHint, destructiveHint, idempotentHint, openWorldHint } }`.
**Data Shape:** `LaunchSuccess { status:"launched", target:"local"|"cloud", conversation_id|null, url|null, initial_status, title|null, workspace?, isolation?, isolation_note?, start_task_id?, backend?, parent_link, parent_link_note? } | LaunchFailure { status:"error", error, guidance }` — guidance strings are written TO THE AGENT ("call … again with a valid target").

### Decisive source
```ts
// 1) Non-idempotency gate — claim BEFORE any network work so a mid-flight replay drops too:
function claimToolCall(parentConversationId, toolCallId) {
  // localStorage["openhands-child-conversation-launches:<parent>"] = string[]
  // corrupt JSON -> fresh ledger; setItem throws (full/unavailable) -> PROCEED (replay risk < never launching)
  if (handled.includes(toolCallId)) return false;
  window.localStorage.setItem(key, JSON.stringify([...handled, toolCallId]));
  return true;
}
export async function handleLaunchChildConversationAction(action, parentId, toolCallId) {
  if (!claimToolCall(parentId, toolCallId)) return;            // replayed ActionEvent: no-op
  const validation = validateLaunchParams(action);             // fills gaps the server schema cannot
  ... result = target === "cloud" ? await launchCloudChild(...) : await launchLocalChild(...);
  await reportLaunchResult(parentId, result).catch(...);       // never throws upward either
}
// 2) Result channel — the agent-server ACKs client tools BEFORE the browser works,
//    so a user-role message is the only way back; prefix hidden in chat (should-render-event):
await sendMessage(parentId, { role: "user", content: [{ type: "text",
  text: `${CHILD_CONVERSATION_RESULT_PREFIX}${JSON.stringify(result)}` }] });
// ...but the server cancels an active /goal loop on ANY inbound message:
if (useGoalStore.getState().statusByConversation[parentId]?.active) return;   // toast only
```

**Flow:** UI registers a `ClientToolSpec` with the agent-server → agent emits an ActionEvent whose `kind` is `ClientAction_<tool-name>` → WS provider routes it to the handler → handler claims the toolCallId in a per-parent localStorage ledger → validates (server pydantic has `extra="forbid"` for unknown/missing/wrong-type, but **the SDK advertises `enum` to the LLM yet drops it when building the model**, so misspelled `target`/`isolation` reach the client, as do cross-target rules like cloud+`isolation`) → launches local (child requests the PARENT's own working dir; server rejects differing workspaces; `worktree`→`new_worktree`, `shared`→`local_repo`; scratch-dir precheck via stored metadata because `git worktree add` cannot branch unborn HEAD and surfaces as a 500) with try-worktree-then-shared fallback reporting WHY, or cloud (pick backend or fail with "ask the user / fall back to local"; inherit repository+git_provider only when the agent named none — provider travels only with inherited repo; send `parent_conversation_id:null` since Cloud filters children-with-parents out of lists; bounded poll 3 s × 180 s for `app_conversation_id`) → reports via prefixed message + toast. Local parent-link honesty is version-gated: older servers ignore unknown fields silently, so compare cached version vs 1.37.1 and say the link was not persisted rather than assume it exists.

**Invariant:** Handler total-no-throw (agent already saw success); every failure becomes corrective guidance naming the exact fix and whether to retry; launches are exactly-once per (conversation, toolCallId) across socket replays (`resend_mode:'all'` fallback) and reload races, claimed before network I/O; degradation notes (`isolation_note`, `parent_link_note`) travel inside the machine-readable result, never as silent behavior change.

**Probe:** Runner block this pass (vitest suite needs node_modules; kept clean read-only tree — standing since pass 1). Executed instead: full-file read of service + spec + constants; byte-pinned excerpts verified at HEAD; test-inventory grep listing all 20 case titles; MCP `get_code_snippet` on both handlers and `check_index_coverage` = `no_recorded_issue` for all five cited files. Direct-test assertions (:195–:535) match every invariant claimed here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openhands", name_pattern: "handle(CanvasUIAction|LaunchChildConversationAction)", fields: ["signature","lines"] });
// executed this pass -> canvas-ui.handleCanvasUIAction 32-64; child-conversation-launch.handleLaunchChildConversationAction 505-536
await mcp.codebase_memory.trace_path({ project: "openhands", function_name: "handleLaunchChildConversationAction", direction: "inbound", depth: 4 });
// executed this pass -> ConversationWebSocketProvider, WebSocketProviderWrapper, AppContent, ConversationView
```

## Verdict
Adopt the ack-first/message-back contract, the pre-network claim ledger with fail-open persistence, enum-gap client validation, and degradation-notes-inside-result for ANY browser-side agent tool. The contrast pair is deliberate: `canvas_ui_control` declares `idempotentHint:true` and needs no ledger; `launch_child_conversation` declares `idempotentHint:false, readOnlyHint:false, openWorldHint:true` and claims before acting — port both halves together. Adapt storage (localStorage → your durable KV) and the toast/i18n layer. Omit OpenHands Cloud provisioning semantics and the specific goal-store coupling (keep the "don't kill a running loop with a bookkeeping message" rule itself). Coverage: `no_recorded_issue` ×5; vitest runner blocked (recorded), deterministic probes substituted.
