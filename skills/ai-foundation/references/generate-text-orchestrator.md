<!-- capsule-v2 -->
# generateText step loop — how does the non-stream orchestrator decide to continue, replay prior approvals, and assemble one step?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory project `ai`. **Question:** When porting a non-streaming multi-step agent loop, what exactly makes the loop take another step, and what must happen before step 0 ever calls the model?

## generateText do-while loop + pre-loop approval replay
**Path/Symbol:** `packages/ai/src/generate-text/generate-text.ts:generateText` (do-while :843–1444; approval replay :703–836; continuation predicate :1434–1444; finishReason-gated output parse :1517–1529).
**Signature:** `async function generateText<TOOLS, RUNTIME_CONTEXT, OUTPUT>({ model, tools, stopWhen = isStepCount(1), output, toolApproval, prepareStep, ... }): Promise<GenerateTextResult>` (232 args block, :568 return type).
**Data Shape:** Inputs: prompt trio (`instructions|system|prompt|messages`, mutually exclusive via `standardizePrompt`), `stopWhen` as single predicate or array (any-met stops). Loop state: `steps[]` of StepResults, `clientToolCalls`, `clientToolOutputs`, `deniedToolApprovalResponses`, `pendingDeferredToolCalls: Map<toolCallId,{toolName}>`, `messagesForNextStep`. Output: `DefaultGenerateTextResult` whose getters flatMap steps; `initialResponseMessages` kept separate so pre-loop tool executions survive in `result.responseMessages`.

### Decisive source
```ts
} while (
  // Continue only after all client tool calls have been executed or denied,
  // and if there are client results or pending deferred provider results.
  clientToolOutputs.length + deniedToolApprovalResponses.length ===
    clientToolCalls.length &&
  (clientToolCalls.length > 0 || pendingDeferredToolCalls.size > 0) &&
  // continue until a stop condition is met:
  !(await isStopConditionMet({ stopConditions, steps }))
);
```

PASS-13 ERRATUM @`9d9a73f1551f2243035491e9de5a2e00ebf9eb17` (#19052): the pre-drift predicate `(all-accounted OR pendingDeferred) && !stop` let a pending DEFERRED provider result independently continue the loop while a client tool call still awaited approval → extra model step → `AI_MissingToolResultsError`. The AND-form above (verified live at `generate-text.ts:1441–1449`) makes all-client-outcomes a HARD precondition; deferred-pending alone can no longer continue a step.

Pre-loop approval replay (:707–733): `collectToolApprovals` reads ONLY the last message when it is role `'tool'`; approved entries are re-validated by `validateApprovedToolApprovals` **filtered to `!toolCall.providerExecuted`**; both collected-denied and revalidation-denied feed `deniedToolApprovalsWithoutResults`; execution runs before any model call and pushes a single `{role:'tool', content:[...]}` message into `initialResponseMessages`.
Output parse (:1517–1529): `if (lastStep.finishReason === 'stop') { resolvedOutput = await (output ?? text()).parseCompleteOutput({ text: lastStep.text }, {...}) }`.

**Flow:** onStart → collect/revalidate/execute prior approvals → loop { throwIfAborted (only when steps.length>0) → arm step timeout → prepareStep overrides → convertToLanguageModelPrompt → retry(doGenerate + response-metadata backfill id/timestamp/modelId) → parseToolCall per part → resolveToolApproval per call (`not-applicable` continues WITHOUT consuming an approval id :1161–1166; user/approved/denied all get signed request parts, only user+denied add to blockedToolCallIds) → executeTools for unblocked client calls → deferred-result bookkeeping (:1325–1352) → asContent → toResponseMessages → DefaultStepResult push → onStepEnd } → while(continuation && !stop) → totalUsage reduce over per-step usage objects with undefined fields preserved → onEnd → conditional output parse.
**Invariant:** The loop continues only when EVERY client tool call has exactly one outcome (an executed output or a denial response) — pass-13 erratum #19052: this is now a HARD precondition, not OR-combinable with deferred-pending; blocked-by-approval calls count toward the denominator via `deniedToolApprovalResponses`. A porter that counts only executed outputs spins forever on denied approvals; one that lets `pendingDeferredToolCalls` continue while an approval pends reproduces the AI_MissingToolResultsError bug #19052 fixed.
**Probe:** `packages/ai/src/generate-text/generate-text.test.ts` — `options.stopWhen` describe (:5148ff: 2-step loop, 2-stop-conditions :6204, isLoopFinished() completion :6522); approval gating "should only execute 1 step when the tool needs approval" (:10535/:10641/:10763) and forged-approval denial (:11222); timeout ladder (:6699–7103 incl. stepMs reuse :6969).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "generateText step loop response messages", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt the two-clause continuation predicate (all-outcomes-accounted AND no pending deferred results AND !stop-condition) and the pre-loop approval-replay phase that executes already-approved tools before step 0. Adapt callback names/aliases and warning logging to host conventions; the `not-applicable`-skips-id-generation rule matters only if you sign approvals. Omit telemetry dispatcher plumbing unless your host has tracing channels. Coverage caveat: index generation 2026-08-16 vs HEAD d25cae2 verified metadata_match for this file.
