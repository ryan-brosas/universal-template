<!-- capsule-v2 -->
# Harness approval continuation recovery — how does a wire payload holding only an approvalId get reattached to the original tool call?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; Codebase Memory `ai`. **Question:** A client returns approval decisions as trailing `tool-approval-response` parts that carry ONLY the approval id — how do you recover the tool name and input needed to resume execution, and which responses must be ignored?

## History-indexed recovery with consumed-approval skip
**Path/Symbol:** `packages/harness/src/agent/harness-agent-tool-approval-continuation.ts` — `collectHarnessAgentToolApprovalContinuations` (:29–94).
**Signature:** `(input: { messages: readonly ModelMessage[] }) => readonly HarnessAgentToolApprovalContinuation[]` where continuation = `{ approvalResponse, toolCall: { type:'tool-call', toolCallId, toolName, input, providerExecuted? } }`.
**Data Shape:** indexes built over ALL messages: toolCallsByToolCallId (from assistant `tool-call` parts) + approvalRequestsByApprovalId (from assistant `tool-approval-request` parts); result ids from the LAST message's `tool-result` parts.

### Decisive source
```ts
const lastMessage = input.messages.at(-1);
if (lastMessage?.role !== 'tool') return [];            // decisions ride ONE trailing tool message
...
for (const part of lastMessage.content) {
  if (part.type !== 'tool-approval-response') continue;
  const approvalRequest = approvalRequestsByApprovalId.get(part.approvalId);
  if (approvalRequest == null) throw new HarnessError({
    message: `Tool approval response '${part.approvalId}' does not match a prior tool approval request.` });
  if (toolResultIds.has(approvalRequest.toolCallId)) continue;   // already consumed by a prior continuation
  const toolCall = toolCallsByToolCallId.get(approvalRequest.toolCallId);
  if (toolCall == null) throw new HarnessError({ /* request references unknown tool call */ });
  continuations.push({ approvalResponse: part, toolCall });
}
```

**Flow:** only the trailing tool message is scanned for responses; each response resolves approvalId → prior assistant approval-request → toolCallId → original tool-call part; responses whose tool already has a result are skipped (idempotent replays), while unmatched ids FAIL LOUDLY instead of being dropped.
**Invariant:** The response envelope is intentionally id-only — the framework must recover call context from history it already has; replaying the same history twice yields ZERO duplicate continuations because consumption is detected via existing results. Companion auto-deny branch lives in run-prompt (:686–707): inactive filtered builtins get `submitToolApproval({approved:false})` WITHOUT any consumer stream parts (test :2214–2262 asserts exactly this).
**Probe:** deterministic probes: `grep -c 'does not match a prior tool approval request' packages/harness/src/agent/harness-agent-tool-approval-continuation.ts` → `1`; `grep -c 'toolResultIds.has' packages/harness/src/agent/harness-agent-tool-approval-continuation.ts` → `1`; direct test `harness-agent.test.ts:1373` ("collects a client-side tool result from messages") exercises the sibling collector.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "collectHarnessAgentToolApprovalContinuations", limit: 3 });
// verified live @9d9a73f — total:1, rank#1 :29-94
```

## Verdict
Adopt id-only response envelopes + history-indexed recovery + consumed-skip; adapt the error type to host taxonomy; omit the builtin/host kind split if the host has no provider-executed tools.
