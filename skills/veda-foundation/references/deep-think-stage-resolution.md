<!-- capsule-v2 -->
# Per-stage model resolution — how do -b/-m flags cascade (or refuse to cascade) into judge/verifier/revision stages?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** When a user sets one backend/model for the CLI, which stage inherits it and which stage must keep its own default?

## expandDeepThinkOptions resolution ladder
**Path/Symbol:** `src/pipelines/deep-think.ts:expandDeepThinkOptions` (:420-750).
**Signature:** `expandDeepThinkOptions(options: DeepThinkOptions): Promise<{solver, judge, verifier, revision, verifyEnabled, forceVerify, traceOptions}>`; delegates to `resolveBackendModel`/`resolveBackendModelForStage` from `../agent/config`.
**Data Shape:** `cliHasBaseOverride = options.backend !== undefined || options.model !== undefined` — one boolean steering three independent fallback ladders.

### Decisive source
```ts
if (cliHasBaseOverride) {
  // Base CLI flags take precedence - use base, not judge
  verifierFallbackBackend = base.backend;
  // Only inherit -m if verifier backend isn't explicitly set
  verifierFallbackModel = options.verifierBackend ? undefined : options.model;
} else {
  // No base override:
  // - cascade backend from judge (keeps "use same provider" behavior)
  // - BUT let verifier model use its own stage default (don't cascade judge model)
  verifierFallbackBackend = judge.backend;
  verifierFallbackModel = undefined;
}
```

**Flow:** base resolved first → solver backends ladder: listedSlots → solverBackends → solverModel (backend inferred FROM model) → [base] ; `-m` + multi-backend distribution THROWS unless listed mode → judge fallback ladder: base-override wins; else first solver's backend when distributing; `judgeFallbackModel = options.judgeBackend ? undefined : options.model` (-m applies to judge only when --judge-backend is absent) → per-backend judgeModels map for pairwise/multi lets EACH judge backend use its OWN default (options.judgeModel deliberately NOT passed down) → verifier ladder above → revision ladder mirrors it with fallback `verifierConfig ?? judge` when no base override.
**Invariant:** A base `-b/-m` must CUT the stage cascade (verifier→judge→revision inheritance exists only in the no-base-override world), otherwise `--judge-model` silently rewrites the verifier; every stage throws loudly (`Unable to resolve model for ... backend`) instead of running on an unintended default; missing solver models are fatal BEFORE any spend.
**Probe:** `tests/pipelines/deep-model-propagation.test.ts` (:10-51 fallbackModel semantics incl. alias-as-fallback; :53+ multi-backend `-m` conflict throw). Not executed this pass (runner scope limited to the six suites pinning new seams); assertions verified at source.
**Coverage caveat:** the full expand function is exercised indirectly via pipeline tests; the pairwise/multi judgeModels-map branch (:606-621) has no dedicated test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "resolveBackendModelForStage fallbackModel cascade", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the base-override-cuts-cascade rule and per-stage loud resolution failures for any multi-stage LLM CLI. Adapt flag names and config precedence. Omit listed-mode slot plumbing if you have no per-solver roster feature.
