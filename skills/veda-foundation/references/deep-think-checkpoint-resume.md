<!-- capsule-v2 -->
# Checkpoint resume reconstruction — how do you restart a pipeline mid-run without re-running completed stages or corrupting candidate identity?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** What state must a checkpoint carry so the solve/judge/verify stages can be skipped deterministically on resume?

## Restore-from-trace ladders
**Path/Symbol:** `src/pipelines/deep-think.ts:runDeepThink` restore branches (:1000-1082 solve, :1211-1226 judge, :1687-1696 verify).
**Signature:** resume gate: `const resumeStageNum = stageOrder[options.resumeCheckpoint.completedStage] ?? 0;` then `skipSolve = isResuming && resumeStageNum >= 1`, `skipJudge = ... >= 2`.
**Data Shape:** Checkpoint carries `successfulCandidateIds: string[]`, `judgeIndexMapping: number[]` (display→original), `judgeSelectedIndex`, `judgeSelectedDisplayIndex` (1-based), `selectedCandidateId`, `verifyChecks?: Check[]`, `partialVerifyResults?: CheckResult[]`, `usageAtCheckpoint`. Trace deep-cloned on resume via `JSON.parse(JSON.stringify(...))`.

### Decisive source
```ts
// Reconstruct successfulToOutputsMap
let successIdx = 0;
for (let i = 0; i < trace.solve.candidates.length; i++) {
  if (candidateIdSet.has(trace.solve.candidates[i].id)) {
    successfulToOutputsMap.set(successIdx++, i);
  }
}
...
// Look up full module from registry to get the prompt
const registryModule = getModuleById(descriptor.id);
return { ..., prompt: registryModule?.prompt ?? '' }; // Fallback to empty if module not found
```

**Flow:** skip-solve → filter trace candidates by checkpoint's successful-ID set, rebuild `successfulToOutputsMap` (successful index → outputs index), rehydrate modules from v3 `promptVariant` (falling back to v2 `module`) with a registry lookup whose miss degrades to an EMPTY prompt (never a crash), rebuild solverMetaMap with backend/model 'unknown' (not stored in trace) → skip-judge → selected answer resolved through the SAME map (`outputsIdx → response`); display index restored as 1-based minus 1 → verify-resume → checkpoint's `verifyChecks` become `checksOverride` (deterministic check regeneration) and `partialVerifyResults` are skipped.
**Invariant:** THREE index spaces exist — original outputs order, successful-candidates order, display order — and every checkpoint field belongs to exactly one; resume must reconstruct the maps rather than reuse array positions or answers land on wrong candidates; usage must be seeded from `usageAtCheckpoint` so combined totals don't reset; uniform candidates get NO registry lookup.
**Probe:** `tests/pipelines/deep-resume.test.ts:133-167` (filters candidates by ID; reconstructs successfulToOutputsMap) + `tests/checkpoint/store.test.ts` — EXECUTED this pass: 10 pass / 0 fail at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "resumeCheckpoint successfulToOutputsMap reconstruct", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt ID-set filtering + explicit map reconstruction + checksOverride for any resumable fan-out pipeline. Adapt the three-index-space vocabulary to your own member ids. Omit v2-promptVariant fallback if you have only one trace schema.
