<!-- capsule-v2 -->
# Programmatic stage entrypoints — how do you expose per-stage pipeline functions to library consumers without exposing the whole generator?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A deep pipeline ships as a CLI generator (`runDeepThink`) but also as a library. How do consumers who want ONE stage (just an ensemble, just judging, just verification) get a clean flat-DTO API, and what invariants do those wrappers add on top of the core kernels?

## Three exported wrappers over the core kernels
**Path/Symbol:** `src/pipelines/deep-think.ts`: `runSolverEnsemble` (:829-863), `runJudgeSelection` (:865-896), `runVerificationPipeline` (:898-956); public re-export at `src/pipelines/index.ts` (:4-6). NOT called internally by `runDeepThink` (which invokes the core kernels directly) — they exist for external consumers.
**Signature:** `runSolverEnsemble(prompt, options: SolverOptions, onEvent?): Promise<RunSolverEnsembleResult>`; `runJudgeSelection(candidates, originalTask, options: JudgeOptions, onMessage?): Promise<RunJudgeSelectionResult>`; `runVerificationPipeline(draft, originalTask, options: VerifierOptions, onMessage?): Promise<RunVerificationPipelineResult>`.
**Data Shape:** flat result DTOs — `RunSolverEnsembleResult {candidates, modules, outputs[{id, module, response, usage?}], usage, errors}`; `RunJudgeSelectionResult {selected, confidence, selectedIndex, consensusAnalysis?, reasoning?, usage, sessionId?}`; `RunVerificationPipelineResult {revised, changes, wasRevised, checks, results, usage, sessionId?}`.

### Decisive source
```ts
  const errors = ensembleResult.outputs.flatMap(o => o.backendErrors ?? []);
  const exceptionErrors = ensembleResult.outputs
    .filter(o => o.error)
    .map(o => o.error!);

  return {
    candidates: ensembleResult.successful,
    modules,
    outputs,
    usage: ensembleResult.totalUsage,
    errors: errors.length > 0 ? errors : exceptionErrors,
  };
```
```ts
export async function runJudgeSelection(
  ...
  if (candidates.length === 0) {
    throw new Error('No candidates to judge');
  }
```
```ts
  if (result.revision && !isUnchanged(result.revision, draft)) {
    return {
      revised: result.revision.revised,
      changes: result.revision.changes,
      wasRevised: true,
      ...
```
(the else branch returns `{revised: draft, changes: [], wasRevised: false, ...}` with the SAME checks/results projection).

**Flow:** each wrapper is plan/project around one core kernel: `runSolverEnsemble` = `planSolverModules` → `buildSolverMembers` → `runEnsemble`, then maps outputs to carry a module descriptor per candidate — uniform members get the placeholder `{id:'none', category:'uniform', name:'Uniform prompt'}` so the DTO never has a missing field → error aggregation prefers `backendErrors` (per-backend stream-level failures) over exception errors, falling back only when no backend errors exist → `runJudgeSelection` guards the degenerate input (empty candidates) with a loud throw BEFORE any backend spend → `runVerificationPipeline` folds the optional revision through `isUnchanged` into a boolean `wasRevised`, so a byte-identical "revision" reports NO change and returns the original draft verbatim.
**Invariant:** The wrapper DTOs are FLAT and total (no missing module descriptor, no nested decision objects) so consumers never reach into kernel internals; degenerate inputs fail loudly before spend (empty candidates); "revised" means byte-different (isUnchanged gate), never "the model ran"; backend-level errors outrank exceptions in the reported error list because they are the more specific diagnosis.
**Probe:** NO dedicated upstream test for the three wrappers (grep over `tests/` finds no import of them; the pure planning seams they compose ARE tested — `tests/pipelines/listed-solver-models.test.ts`). Source-pinned probe: `grep -rn "runSolverEnsemble\|runJudgeSelection\|runVerificationPipeline" src/ tests/` → definition sites plus exactly the three re-export lines in `src/pipelines/index.ts`; zero internal callers.
**Coverage caveat:** these are the public library surface; a porting test should pin "empty candidates throws before I/O" and "byte-identical revision ⇒ wasRevised false" since neither has an upstream pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "runSolverEnsemble runJudgeSelection runVerificationPipeline", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the thin-wrapper pattern: one exported flat-DTO function per stage over shared core kernels, loud pre-spend guards, total DTOs with explicit placeholders, and byte-equality semantics for "changed". Adapt DTO shapes to your consumers. Omit the wrappers if your pipeline is CLI-only — the generator alone suffices.
