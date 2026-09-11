<!-- capsule-v2 -->
# Per-stage model resolution — how do -b/-m flags cascade (or refuse to cascade) into judge/verifier/revision stages?

**Source:** veda MIT `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6` (pass-8 re-adjudication: `git diff f050518c..c3c69f2 -- src/pipelines/deep-think.ts` is EMPTY — this seam is byte-identical across the pin advance; cited excerpt verified byte-for-byte); Codebase Memory `veda`. **Question:** When a user sets one backend/model for the CLI, which stage inherits it and which stage must keep its own default?

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
**Invariant:** A base `-b/-m` must CUT the stage cascade (verifier→judge→revision inheritance exists only in the no-base-override world), otherwise `--judge-model` silently rewrites the verifier. Resolution failure is ASYMMETRIC by design: solver (:516) and judge (:600) throw loudly (`Unable to resolve model for ... backend`) BEFORE any spend, but an unresolvable verifier/revision degrades to a `null` config — an enabled verify then silently does not run (`shouldVerify` requires `verifier !== null`), so a misconfigured verify stage fails QUIETLY rather than loudly.
**Probe:** `tests/pipelines/deep-model-propagation.test.ts` (:10-51 fallbackModel semantics incl. alias-as-fallback; :53-67 multi-backend `-m` conflict throw). EXECUTED pass 8 at c3c69f2: 4 pass / 0 fail.
**Coverage caveat:** the full expand function is exercised indirectly via pipeline tests; the pairwise/multi judgeModels-map branch (:606-621) has no dedicated test.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "resolveBackendModelForStage fallbackModel cascade", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the base-override-cuts-cascade rule and per-stage loud resolution failures for any multi-stage LLM CLI. Adapt flag names and config precedence. Omit listed-mode slot plumbing if you have no per-solver roster feature.
