<!-- capsule-v2 -->
# Last-step completion predicates — how does "may the loop fire another request" read from a UI message history, and why do provider-executed calls never count?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What exact state of the LAST assistant step authorizes auto-continuation, for client tool calls vs approval responses?

## The predicate pair
**Path/Symbol:** `packages/ai/src/ui/last-assistant-message-is-complete-with-tool-calls.ts:lastAssistantMessageIsCompleteWithToolCalls` (38L whole) and `packages/ai/src/ui/last-assistant-message-is-complete-with-approval-responses.ts:lastAssistantMessageIsCompleteWithApprovalResponses` (42L whole).
**Signature:** both `({messages: UIMessage[]}): boolean` — synchronous, total (never throw), safe as a `sendAutomaticallyWhen` callback.

### Decisive source
```ts
// tool-calls variant :22-37:
const lastStepStartIndex = message.parts.reduce((lastIndex, part, index) =>
  part.type === 'step-start' ? index : lastIndex, -1);
const lastStepToolInvocations = message.parts
  .slice(lastStepStartIndex + 1)
  .filter(isToolUIPart)
  .filter(part => !part.providerExecuted);        // <-- provider calls NEVER gate
return lastStepToolInvocations.length > 0 &&      // at least one CLIENT call
  lastStepToolInvocations.every(part =>
    part.state === 'output-available' || part.state === 'output-error');
// approval variant :26-41 — same window, but providerExecuted NOT filtered:
const lastStepToolInvocations = message.parts.slice(lastStepStartIndex + 1).filter(isToolUIPart);
return lastStepToolInvocations.filter(p => p.state === 'approval-responded').length > 0 && // ≥1 answered
  lastStepToolInvocations.every(p =>
    p.state === 'output-available' || p.state === 'output-error' ||
    p.state === 'approval-responded');            // no pending approvals remain
```

**Flow:** guard clauses first — empty history ⇒ false; last message not assistant ⇒ false. Then reduce to the LAST `step-start` index (multi-step messages replay only the final step) and slice the tail window. Tool-calls variant: ≥1 non-provider-executed invocation AND all such invocations terminal (`output-available` counts success, `output-error` counts failure — an errored call is still COMPLETE). Approval variant: ≥1 `approval-responded` AND zero parts still in `approval-requested` — mixed steps where one tool already ran and another awaits approval stay false until every approval is answered.
**Invariant:** these are the canonical `sendAutomaticallyWhen` implementations (HITL auto-resume): consumed by `ui/chat.ts` inside addToolResult (:531-548) / addToolOutput (:580-597) and onFinish (:876) via `shouldSendAutomatically()` (:613-628) — the auto-send fires UN-awaited inside the SerialJobExecutor job ("no await to avoid deadlocking") and only when status ∉ {streaming, submitted}. The providerExecuted asymmetry IS the contract: server-executed tools already finished on the provider side, so their presence must neither trigger nor block a client-tool continuation — but approval gating must see ALL tools because a pending provider-side approval still needs the user's answer. Porting the filter onto the approval variant deadlocks HITL; dropping it from the tool-calls variant makes streams self-continue spuriously.

**Probe:** `bash -c "grep -n \"should return false for complete provider executed tool calls\\|should return false when provider-executed tool is approval-responded but regular tool is still approval-requested\\|should return true when there is a text part after the last tool result\" /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui/last-assistant-message-is-complete-with-tool-calls.test.ts /mnt/hdd/utopia/inspo/ai/packages/ai/src/ui/last-assistant-message-is-complete-with-approval-responses.test.ts"` → :341 (tool-calls) and :199 (approval).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "lastAssistantMessageIsCompleteWithToolCalls lastAssistantMessageIsCompleteWithApprovalResponses sendAutomaticallyWhen", limit: 6, fields: ["signature","name","file"] });
```

## Verdict
Adopt the last-step-window reduction and both truth tables verbatim — especially the providerExecuted filter present ONLY in the tool-calls variant. Adapt message/part type names to your schema. Omit nothing else; each file is one function.
