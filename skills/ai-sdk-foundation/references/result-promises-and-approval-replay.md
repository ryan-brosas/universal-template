<!-- capsule-v2 -->
# Pre-loop approval replay in streamText — how do approved/denied tool calls from a PRIOR run execute before step 0 so the model sees a consistent history?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** What must the synthetic "step -1" tool-execution stream emit, and which revalidation rules stop stale approvals from auto-executing?

## The initial tool-execution step stream
**Path/Symbol:** `packages/ai/src/generate-text/stream-text.ts:1674–1818` — `collectToolApprovals({messages: initialMessages})`, then `validateApprovedToolApprovals`, then a hand-built `toolExecutionStepStream` stitched FIRST via `self.addStream`; results land in `initialResponseMessages` resolved through `_initialResponseMessages`.
**Signature:** filter provider-executed approvals out of revalidation (`toolApproval.toolCall.providerExecuted`), execute local approved calls via `executeToolCall` under `Promise.all`, enqueue `tool-output-denied` parts for denials, coalesce outputs into ONE `{role:'tool', content: ToolContent}` message.
**Data Shape:** `localDeniedToolApprovalsWithoutResults` get synthesized `output: {type:'execution-denied', reason}` results; approvals that ALREADY carry `existingToolResult` are skipped (no duplicate tool messages).

### Decisive source
```ts
const {
  approvedToolApprovals: localApprovedToolApprovals,
  deniedToolApprovals: revalidationDeniedToolApprovals,
} = await validateApprovedToolApprovals({
  approvedToolApprovals: approvedToolApprovals.filter(
    toolApproval => !toolApproval.toolCall.providerExecuted,
  ),
  ...
});
...
for (const toolApproval of [
  ...localDeniedToolApprovals,
  ...deniedProviderExecutedToolApprovals,
]) {
  toolExecutionStepStreamController?.enqueue({
    type: 'tool-output-denied',
    toolCallId: toolApproval.toolCall.toolCallId,
    toolName: toolApproval.toolCall.toolName,
  } as StaticToolOutputDenied<TOOLS>);
```
(stream-text.ts:1680–1732, verbatim)

```ts
} finally {
  toolExecutionStepStreamController?.close();
}
...
self._initialResponseMessages.resolve(initialResponseMessages);
```
(:1813–1818)

**Flow:** run starts → split initial-message approvals into approved/denied → REVALIDATE approved ones against current tools/config/secret (state may have changed between turns) → denied ones (local + provider-executed) become visible `tool-output-denied` stream parts BEFORE any model output → approved executions run CONCURRENTLY, preliminary results streamed via `onPreliminaryToolResult` → outputs + denial stubs coalesce into ONE tool-role response message prepended to history → step 0's prompt = initialMessages + these response messages.
**Invariant:** (1) Revalidation happens EVERY run — a signed approval from a previous turn must never auto-execute against changed config; provider-executed calls are exempt because their results live server-side. (2) The synthetic stream is added to the stitcher BEFORE step 0's stream so consumers observe denial/execution parts in causal order. (3) Denied calls still produce a tool-result (`execution-denied`) in history — omitting it leaves an orphan tool-call that providers reject next turn. (4) `finally { controller.close() }` guarantees the stitched stream terminates even when executions throw.
**Probe:** orchestrator twin replays identically (`generate-text.ts`, see `generate-text-orchestrator.md`); collection/validation pinned by `collect-tool-approvals.test.ts` + `validate-tool-approvals.test.ts`; HMAC gate order covered in `approval-round-trip.md`.

## Result-promise wiring around the replay
The `_initialResponseMessages` DelayedPromise resolves ONLY after the replay finishes (:1818) and `.responseMessages` awaits it alongside `_steps` (:2595–2603) — callers can never assemble history mid-replay. Promise-lifecycle mechanics of DelayedPromise itself are owned by `lazy-result-primitives.md`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "toolExecutionStepStream tool-output-denied", limit: 10 });
await mcp.codebase_memory.search_graph({ project: "ai", query: "initialResponseMessages responseMessages", limit: 5 });
```

## Verdict
Adopt per-run revalidation, denial-as-tool-result history, first-position stitching, and close-in-finally. Adapt approval storage/signing to your host. Omit sandbox plumbing in execution. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
