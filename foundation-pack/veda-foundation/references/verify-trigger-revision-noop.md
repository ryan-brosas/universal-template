<!-- capsule-v2 -->
# Verification gating + revision no-op — when does a draft get verified at all, and how is "the model rewrote nothing" detected?

**Source:** veda MIT `master@f050518c99fa54a5a0af4a04918aaf01d1ed94e1`; Codebase Memory `veda`. **Question:** What triggers verification, and why must revision application compare bytes instead of trusting the reviser's own changed-flag?

## shouldVerify trigger + isUnchanged guard
**Path/Symbol:** `src/pipelines/deep-think.ts` verify trigger (:1675-1681) and both `isUnchanged` call sites (:917, :1856); `src/core/verify.ts:isUnchanged` (:45-47).
**Signature:** `isUnchanged(revision: Revision, originalDraft: string): boolean` → `revision.revised === originalDraft`; `const shouldVerify = verifyEnabled && verifier !== null && (judgeConfidence < 0.7 || isCloseRace || forceVerify)` where `isCloseRace = trace.judge.mode === 'multi' && winMargin < 0.15`.
**Data Shape:** `Revision {revised, changes[], conflicts[]}`; verdict vocabulary `'supports' | 'contradicts' | 'uncertain'`; revision runs ONLY when `contradictions > 0` (uncertain never triggers it).

### Decisive source
```ts
export function isUnchanged(revision: Revision, originalDraft: string): boolean {
  return revision.revised === originalDraft;
}
...
if (!isUnchanged(revisionResult.revision, finalAnswer)) {
  finalAnswer = revisionResult.revision.revised;
  wasRevised = true;
```

**Flow:** verification gate combines THREE independent triggers (low confidence <0.7, close multi-judge race winMargin<0.15, force flag) AND requires a resolved verifier config → checks generated then answered (parallel, per-check handler factory closes over index/id to prevent event interleaving) → contradictions>0 spawns revision with ONLY the contradicting results as input → revised answer replaces finalAnswer ONLY if byte-different; identical text ⇒ wasRevised stays false, changes discarded, session/backend not re-pointed.
**Invariant:** NEVER trust a reviser's self-reported "I changed things" — LLMs echo drafts verbatim while emitting change lists; the byte comparison is THE no-op detector on both the pipeline path and runVerificationPipeline; `winMargin ?? 1.0` default keeps non-multi modes out of close-race territory.
**Probe:** `tests/core/verify-primitives.test.ts` + `tests/core/verify.test.ts` exist for the verify plane; the two isUnchanged call sites are pinned indirectly via `tests/pipelines/deep-think.test.ts`. Runner scope this pass covered judge/modules/spawn suites; verify suites not executed — assertions verified at source :45-47.
**Coverage caveat:** no direct unit test names isUnchanged at this HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-ecosystem-veda", query: "isUnchanged shouldVerify contradiction", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt the three-trigger OR-gate and byte-equality no-op detection for any generate→verify→revise loop. Adapt thresholds (0.7 / 0.15) to your confidence calibration. Omit per-check handler factories if your checks run sequentially.
