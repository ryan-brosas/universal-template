<!-- capsule-v2 -->
# DeepThink stage machine — how do you orchestrate solve→judge→verify→revise so every stage is checkpointed, resumable, and event-ordered?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** How does a multi-stage LLM pipeline emit ordered events while persisting a resume point after each stage, without losing stage attribution on failure?

## runDeepThink background-producer over AsyncQueue
**Path/Symbol:** `src/pipelines/deep-think.ts:runDeepThink` (:958-1954); queue from `../util` AsyncQueue.
**Signature:** `runDeepThink(prompt: string, options?: DeepThinkOptions): AsyncGenerator<DeepThinkEvent>`; options carry `onCheckpoint?(DeepThinkCheckpointData)` and `resumeCheckpoint?`.
**Data Shape:** `DeepThinkCheckpointData {trace, status:'partial'|'complete', completedStage:'solve'|'judge'|'verify', failedStage?:'judge'|'verify'|'revision', error?, successfulCandidateIds, judgeSeed?, judgeIndexMapping?, judgeSelectedIndex?, judgeSelectedDisplayIndex?, selectedCandidateId?, verifyChecks?, partialVerifyResults?, usageAtCheckpoint}`. Stage order map `{solve:1, judge:2, verify:3}` drives skip logic.

### Decisive source
```ts
// currentStage: where we are now (for failure attribution)
// lastCompletedStage: last successfully completed stage (safe resume point)
let currentStage: CurrentStage = 'init';
let lastCompletedStage: LastCompletedStage = 'none';
...
} catch (e) {
  ...
  // Only record failedStage for stages that can meaningfully fail (judge, verify, revision)
  if (options.onCheckpoint && lastCompletedStage !== 'none' && trace) {
    const failedStage = currentStage === 'judge' || currentStage === 'verify' || currentStage === 'revision'
      ? currentStage : undefined;
    try { await options.onCheckpoint(failureCheckpoint); }
    catch (checkpointError) {
      // Don't let checkpoint write failures swallow the original error
    }
  }
  queue.fail(e instanceof Error ? e : new Error(errorMessage));
}
yield* queue;
```

**Flow:** whole body runs in an IIFE task pushing events into one AsyncQueue; generator yields from the queue so consumers get events in emission order while stages run → after solve / judge / verify each: `await onCheckpoint({status:'partial', completedStage, usageAtCheckpoint})` then push a `checkpoint` event → verification triggers are `confidence < 0.7 || (mode==='multi' && winMargin < 0.15) || forceVerify` → revision only when contradictions > 0 AND a revision config resolved; `isUnchanged(revision, draft)` guards both wasRevised flips → catch writes a FAILURE checkpoint (completedStage = safe resume point, failedStage = where it broke) before failing the queue.
**Invariant:** `lastCompletedStage` (safe resume) and `currentStage` (failure attribution) are tracked SEPARATELY — conflating them makes a crash inside judge either lose the solve checkpoint or mislabel the failure; checkpoint-write failures must never mask the original pipeline error; all-solvers-failed is terminal (error + done), partial solver failures continue.
**Probe:** `tests/pipelines/deep-resume.test.ts` (:112-131 stage-order, :168-213 error-checkpoint data incl. failedStage vocabulary, :214-250 partial verify resume) — EXECUTED this pass: 10 pass / 0 fail at HEAD.
**Coverage caveat:** the full generator body has no end-to-end test; the resume tests pin data shapes and reconstruction helpers, not the IIFE control flow itself.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "runDeepThink checkpoint completedStage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual stage trackers, per-stage checkpoint callback + event pair, confidence/win-margin verification triggers, and fail-safe catch ordering. Adapt stage names and checkpoint schema to your domain. Omit Bun-specific hashing (`Bun.hash` for promptHash) if not on Bun.
