<!-- capsule-v2 -->
# Pinned-base suppression — how do you make an explicitly user-chosen base backend/model suppress config-driven stage defaults without breaking explicit per-stage flags?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A multi-stage LLM CLI (solver→judge→verifier→revision) has per-stage config defaults. When the user passes `-b codex` or `-m opus`, the config's `deep.judgeModel` / `deep.distributeSolvers` must NOT silently override the user's visible choice — but an explicit `--judge-model` or `--distribute-solvers` flag must still win. How is that precedence encoded?

## Connected graph-selected seam
**Path/Symbol:** `src/cli/resolve.ts`: `isBasePinned` (:66–68), `resolveSolverConfig` useDistributed ladder (:297–301), `resolveJudgeConfig` (:378–421), `resolveVerifierConfig` (:423–467), `resolveRevisionConfig` (:469–522), `resolveStageReasoning` (:553–614); composed by `resolveDeepStages` (:185–195) and called from `src/cli/index.ts:constructDeepInput` (:184–281) for the live `veda deep` argv path.
**Signature:** `isBasePinned(source: ResolutionSource): boolean`; `resolveDeepStages(opts: {flags, baseResolved, globalConfig?}): StageConfigs`.
**Data Shape:** `ResolutionSource = 'explicit' | 'alias' | 'prefix' | 'config' | 'default'` (types.ts:179) — the pinning decision is a predicate over the base resolution's SOURCE TAG, not a re-check of flags. `StageConfigs { solver: SolverConfig (fixed|distributed|listed union), judge/verifier/revision: StageConfig {backend, model, reasoning?} }`.

### Decisive source
```ts
// The whole pinning concept in one predicate:
function isBasePinned(source: ResolutionSource): boolean {
  return source === 'explicit' || source === 'alias' || source === 'prefix';
}
// Solver distribution ladder — tri-state CLI flag > pinned suppression > config:
  const useDistributed = flags.distributeSolvers !== undefined
    ? flags.distributeSolvers  // Explicit CLI flag always wins
    : isBasePinned(base.source)
      ? false  // Pinned base suppresses config distribution
      : (deepConfig?.distributeSolvers ?? false);
// Judge stage — the per-stage pattern (verifier mirrors it verbatim):
  const basePinned = isBasePinned(base.source);

  // If judge model is an alias, let it drive the backend
  // When base is pinned and no stage-specific flags, use base model (not config)
  const judgeModel = flags.judgeModel ?? (basePinned ? flags.model : deepConfig?.judgeModel);
  const judgeModelAlias = judgeModel ? resolveModelAlias(judgeModel, globalConfig?.modelAliases) : undefined;

  // Judge backend: CLI > alias-inferred > (pinned base | config) > base
  const effectiveBackend = flags.judgeBackend
    ?? (judgeModelAlias ? judgeModelAlias.backend : undefined)
    ?? (basePinned ? base.backend : deepConfig?.judgeBackend);
// Revision — inherits verifier's choice when nothing else is set:
  const effectiveBackend = flags.revisionBackend
    ?? (revisionModelAlias ? revisionModelAlias.backend : undefined)
    ?? (basePinned ? base.backend : (deepConfig?.revisionBackend ?? flags.verifierBackend ?? deepConfig?.verifierBackend));

  // For model fallback: when base is pinned, use flags.model; otherwise use config/verifier cascade
  const modelFallback = basePinned
    ? flags.model
    : (revisionModel ?? flags.verifierModel ?? deepConfig?.verifierModel ?? flags.model);
```

**Flow:** base resolves once (`resolveBackendModel`) and carries its winning `source` tag. Each stage then runs the same shape: per-stage CLI flag → alias-inferred backend → (pinned base | config default) → base fallback. When `isBasePinned(base.source)`, the config layer is REPLACED by the base's own backend/model — so `-b agy` with a config `deep.judgeModel: gpt-5.6-sol` keeps the judge on agy instead of leaking the codex model. The solver adds the distribution ladder above; an explicit `--distribute-solvers` (even `=false`) always wins because the check is `!== undefined` (tri-state). Reasoning follows the same family: `resolveStageReasoning` precedence is per-stage CLI flag > base `-r` (which suppresses ALL per-stage config defaults) > alias reasoning hint > config > stage default (`medium` for solver/judge, `high` for verifier/revision) — and revision RECURSES into verifier's effective reasoning when nothing is set, so changing verifier reasoning silently moves revision too.
**Invariant:** "user personally chose" (explicit/alias/prefix source tags) suppresses config-driven stage behavior; config-derived or default bases do NOT; explicit per-stage CLI flags and the tri-state distribute flag always beat the suppression; every stage resolves through the same shared `resolveBackendModel` so unknown models throw loudly at resolution time, not mid-run.
**Probe:** `tests/cli/resolve-pinned-base.test.ts` (executed green at pin: 8 pass / 0 fail within the 39-test batch) — pins all five source-tag arms: explicit/alias/prefix bases each yield `mode:'fixed'` on the solver despite config `distributeSolvers:true` + three `solverBackends`; config and default sources yield `mode:'distributed'`; `--distribute-solvers=true` re-enables under a pinned base; `--distribute-solvers=false` stays fixed; `--solver-backend droid` overrides `-b codex`. Reasoning recursion arm pinned in `tests/cli/resolve-solver-models.test.ts` ("base -r overrides per-slot alias hints").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "isBasePinned resolveJudgeConfig resolveVerifierConfig resolveRevisionConfig resolveStageReasoning", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the source-tag predicate pattern: record WHY the base was chosen at resolution time, and let downstream stages branch on that tag instead of re-inspecting flags — it keeps "user intent" vs "config convenience" separable even when both produce the same backend string. Adopt the tri-state check (`flag !== undefined`) for any opt-in/opt-out pair where the user must be able to force EITHER side over config. Adapt the stage list, the config namespace, and the stage-default table to your pipeline. Omit the revision-inherits-verifier recursion if your stages are independent — but if you keep it, document it: it is a silent coupling porters will miss. Note the relationship: this is the CLI plane; the pipeline-plane twin `expandDeepThinkOptions` (see `deep-think-stage-resolution.md`) implements the same base-override-cuts-cascade rule for programmatic entry points.
