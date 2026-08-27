<!-- capsule-v2 -->
# Stream-text continuation engine — when does a finished step chain into the next model call, and how do deferred provider results keep the loop alive?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** Where is the stream-time continuation decision made and what exact predicate (including `pendingDeferredToolCalls`) must a porter reproduce?

## The flush-time continuation predicate
**Path/Symbol:** `packages/ai/src/generate-text/stream-text.ts` — per-step TransformStream `flush` (2328–2464); predicate at 2424–2437; recursion into `streamStep` at 2440–2445.
**Signature:** inside `flush`: continue iff `allClientToolCallsAccountedFor && (clientToolCalls.length > 0 || pendingDeferredToolCalls.size > 0) && !(await isStopConditionMet({stopConditions, steps: recordedSteps}))` — pass-13 erratum #19052: all-accounted is now a HARD AND-precondition, not an OR-alternative.
**Data Shape:** `clientToolCalls` = step tool-calls with `providerExecuted !== true`; accounted = count equals client outputs + denied approval responses; `pendingDeferredToolCalls: Map<toolCallId, {toolName}>` lives in the CONSTRUCTOR closure so it persists across steps.

### Decisive source
```ts
if (
  // Continue only after all client tool calls have been executed or denied,
  // and if there are client results or pending deferred provider results.
  clientToolCalls.length ===
    clientToolOutputs.length +
      deniedToolApprovalResponses.length &&
  (clientToolCalls.length > 0 ||
    pendingDeferredToolCalls.size > 0) &&
  // continue until a stop condition is met:
  !(await isStopConditionMet({
    stopConditions,
    steps: recordedSteps,
  }))
) {
```
(stream-text.ts ~:2503–2515 @`9d9a73f1551f2243035491e9de5a2e00ebf9eb17`; pre-drift pin was :2424–2438)

PASS-13 ERRATUM (#19052): the pre-drift OR-form `(allAccounted || pendingDeferred)` let a deferred provider result continue the stream while a client tool approval was still pending, producing a doomed extra model step. Upstream changed it to the AND-form above — all client outcomes accounted is now a hard precondition in BOTH generateText and streamText (stream-text twin at `generate-text.ts:1441–1449`).

```ts
// Track provider-executed tool calls that support deferred results.
for (const toolCall of stepToolCalls) {
  if (toolCall.providerExecuted !== true) continue;
  const tool = getOwn(stepExecutionTools, toolCall.toolName);
  if (tool?.type === 'provider' && tool.supportsDeferredResults) {
    const hasResultInStep = stepToolOutputs.some(
      output =>
        (output.type === 'tool-result' || output.type === 'tool-error') &&
        output.toolCallId === toolCall.toolCallId,
    );
    if (!hasResultInStep) {
      pendingDeferredToolCalls.set(toolCall.toolCallId, { toolName: toolCall.toolName });
    }
  }
}
// Mark deferred tool calls as resolved when we receive their results
for (const output of stepToolOutputs) {
  if (output.type === 'tool-result' || output.type === 'tool-error') {
    pendingDeferredToolCalls.delete(output.toolCallId);
  }
}
```
(:2385–2419)

**Flow:** step stream closes → if NO terminal chunk AND no output chunk, enqueue `NoOutputGeneratedError` and close (incomplete streams with PARTIAL output instead keep their partial result) → emit synthetic `finish-step` → await `stepFinish.promise` (event processor has fully recorded the step BEFORE continuation logic reads `recordedSteps` — this handshake is what makes stop predicates see complete history) → classify deferred provider calls (no result yet → pending; any result/error arrives → delete) → evaluate the two-clause predicate → recurse `streamStep(currentStep + 1, combinedUsage)` or enqueue terminal `finish` + `closeStream()`.
**Invariant:** (1) Continuation requires BOTH "work remains" AND "no stop condition" — checking only one double-executes tools or strands results. (2) Deferred tracking is cross-step state on the run, NOT per-step — a porter who resets the Map each step loops forever on provider-executed tools like code execution that return results a turn later. (3) `deniedToolApprovalResponses` count as settled outcomes; forgetting them re-prompts denied tools endlessly. (4) The `stepFinish` DelayedPromise handshake orders recording before deciding — without it stop conditions race the ledger.
**Probe:** `stream-text.test.ts:25377` ("correct stream parts including tool calls and deferred results"), `:25886–25902` deferred resolution incl. tool-error twin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "pendingDeferredToolCalls supportsDeferredResults continuation", limit: 10 });
```

## Verdict
Adopt the two-clause predicate, the constructor-closure deferred map with result-keyed deletion, the denial-counts-as-settled rule, and the stepFinish handshake before evaluating stop conditions. Adapt the account-set definition to your host's approval model. Omit tracing-channel context wrapping (Node diagnostics-specific). Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2; decisive ranges read at HEAD this session.
