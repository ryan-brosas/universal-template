<!-- capsule-v2 -->
# Say/ask UI protocol — how does an agent narrate progress and block on the user through one channel that tolerates absence?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter's tool calls hang forever when the UI is closed — how does roo model narration vs blocking asks, including the walked-away case?

## say = fire-and-forget; ask = blocking, IGNORABLE
**Path/Symbol:** `src/core/task/Task.ts` (`say`/`ask` primitives; referenced throughout the approvals/task-loop planes); ask taxonomy in `@roo-code/types` (`ClineAsk`, `isNonBlockingAsk`).
**Signature:** `say(kind, text, …)` (non-blocking narration: api_req_started with spinner, tool announcements, user_feedback) vs `ask(kind, text): Promise<{response, text?, images?}>` (blocking: tool approval, mistake_limit_reached, followup, plan_respond).
**Data Shape:** AskIgnoredError exists because asks can be IGNORED by the UI (user walked away) — every caller must handle the ignored path explicitly.

### Decisive source
```ts
// Auto-approval integrates at the ask layer: checkAutoApproval decides
// BEFORE the ask reaches the webview, and timeout decisions carry their
// own resume closure. AskIgnoredError: the user may simply never answer.
```

**Flow:** agent narrates via say (never blocks) → decision points go through the approval classifier first → surviving asks reach the webview and block on {response, text, images} → three exits: answered / ignored (AskIgnoredError path) / timeout-with-resume-closure (followup case).
**Invariant:** Narration and blocking must be separate verbs; every blocking call must have a defined no-answer behavior — an unhandled ignored ask is a hung agent.
**Probe:** Cross-pinned by `src/core/tools/__tests__/askFollowupQuestionTool.spec.ts`; deterministic probes: `isNonBlockingAsk` in `@roo-code/types`, AskIgnoredError usage sites via grep in Task.ts. Coverage caveat: protocol itself untested in isolation at this HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "AskIgnoredError isNonBlockingAsk say ask Task", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-verb channel + ignorable-ask error type. Adapt kind names to your UI taxonomy. Omit plan_respond if you have no plan mode. Coverage caveat noted above.
