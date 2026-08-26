<!-- capsule-v2 -->
# Do-while/until loop cancellation triple — where must a long loop check for abort?

**Source:** mastra Apache-2.0 `main@502653550fb45d8e72dfdd57732161f9176dbcf2`; Codebase Memory `ext-mastra`. **Question:** At which points does the loop executor honor run cancellation, and how does iteration counting survive resume?

## Three abort checks per iteration; resume continues from metadata, not zero
**Path/Symbol:** `packages/core/src/workflows/handlers/control-flow.ts:executeLoop` (:632-867).
**Signature:** `executeLoop(engine, params)` with `entry: { type:'loop'; step; condition; loopType: 'dowhile'|'dountil' }`.
**Data Shape:** `let isTrue = true`; iteration seeded from persisted state: `const prevIterationCount = stepResults[stepId]?.metadata?.iterationCount; let iteration = prevIterationCount ? prevIterationCount - 1 : 0`. Loop input prefers the step's own prior payload over upstream output: `loopInput = prevStepResult && hasOwnProperty(prevStepResult,'payload') ? prevStepResult.payload : prevOutput`.

### Decisive source
```ts
do {
  if (abortController?.signal?.aborted) { ...endChildSpan(...early); return { status:'canceled' }; }
  const stepExecResult = await executeChildEntry(engine, step, {...prevOutput: result.output...});
  ...
  currentRestart = undefined; currentTimeTravel = undefined;
  // Clear resume for next iteration only if the step has completed resuming
  if (currentResume && result.status !== 'suspended') { currentResume = undefined; }
  if (result.status !== 'success') { ...return result; }
  if (abortController?.signal?.aborted) { ...return { status:'canceled' }; }   // post-execution check
  isTrue = await condition(createDeprecationProxy({...iterationCount: iteration+1...}));
  ...
  iteration++;
  if (abortController?.signal?.aborted) { ...return { status:'canceled' }; }   // post-condition check
} while (entry.loopType === 'dowhile' ? isTrue : !isTrue);
```

**Flow:** abort-check → execute body with previous output → clear restart/timeTravel always, resume ONLY when not still suspended → non-success returns early (span ended `.early`) → abort-check → evaluate condition → increment → abort-check again.
**Invariant:** The three checks bracket the two awaits; a condition that calls `abort()` and then returns a terminal value must NOT let the loop exit as 'success' (the third check owns that). `currentRestart`/`currentTimeTravel` are cleared after ONE iteration while `currentResume` survives across suspended iterations so the same resume data isn't consumed twice. Iteration count resumes at `metadata.iterationCount - 1`, never restarts at 0.
**Probe:** `grep -c "abortController?.signal?.aborted" packages/core/src/workflows/handlers/control-flow.ts` from repo root (=7 total file-wide; 3 belong to executeLoop :694/:759/:841). Direct test: `packages/core/src/workflows/cancel-sleep.test.ts` pins cancel-during-sleep semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mastra", query: "executeLoop dowhile dountil condition iteration", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the triple-abort placement and resume-seeded iteration counter verbatim. Adapt `abortableSleep`-backed condition/step durability via your own engine hooks. Omit watch-event emission details if your host has no event stream.
