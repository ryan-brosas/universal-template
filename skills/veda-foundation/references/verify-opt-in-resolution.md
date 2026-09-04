<!-- capsule-v2 -->
# Verify opt-in resolution — how do you model an expensive opt-in feature with three flags where two pairs conflict but one pair composes, resolved into a closed discriminated union?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** Deep runs have a verifier+revision phase that is OFF by default (it costs extra LLM spend). The user can pass `--verify`, `--force-verify` (verify even when confidence would skip it), or `--no-verify`. Two of the three pairs are nonsense (`--verify --no-verify`, `--no-verify --force-verify`) but one composes (`--verify --force-verify`). How do you encode that so the downstream pipeline sees a closed type, not three booleans?

## Connected graph-selected seam
**Path/Symbol:** `src/cli/resolve.ts:resolveVerifyConfig` (:524–533); type `src/cli/types.ts:VerifyConfig` (:87–89); conflict arms in `src/cli/validate.ts:detectConflicts` (:237–253); wired at `src/cli/index.ts:constructDeepInput` (:273, `verify: resolveVerifyConfig(flags)`).
**Signature:** `resolveVerifyConfig(flags: RawFlags): VerifyConfig`; `detectConflicts(flags: RawFlags): void` (throws).
**Data Shape:** `VerifyConfig = { enabled: false } | { enabled: true; forced: boolean }` — a closed discriminated union. `{ enabled: true }` without `forced` is unrepresentable; `{ enabled: false, forced: true }` is unrepresentable. Downstream (`runDeepThink`) branches on `enabled` and reads `forced` only in the enabled arm.

### Decisive source
```ts
export function resolveVerifyConfig(flags: RawFlags): VerifyConfig {
  if (flags.noVerify) {
    return { enabled: false };
  }
  if (flags.verify || flags.forceVerify) {
    return { enabled: true, forced: !!flags.forceVerify };
  }
  // Off by default — verifier + revision only run when explicitly opted in
  // with --verify (or --force-verify).
  return { enabled: false };
}
```
```ts
// src/cli/validate.ts — the conflict cluster (resolution and validation are SEPARATE steps):
export function detectConflicts(flags: RawFlags): void {
  // --verify vs --no-verify
  if (flags.verify && flags.noVerify) {
    throw new CliValidationError(
      'Cannot use --verify and --no-verify together',
      'MUTUALLY_EXCLUSIVE_FLAGS'
    );
  }

  // --no-verify vs --force-verify
  if (flags.noVerify && flags.forceVerify) {
    throw new CliValidationError(
      'Cannot use --no-verify and --force-verify together',
      'MUTUALLY_EXCLUSIVE_FLAGS'
    );
  }
```

**Flow:** the argv ladder (see `argv-validation-ladder.md`) runs `detectConflicts` BEFORE resolution: the two nonsense pairs throw `MUTUALLY_EXCLUSIVE_FLAGS` at validation time; `--verify --force-verify` passes through because no arm matches it. Then `resolveVerifyConfig` collapses the surviving flag combinations into the union with a fixed order: `noVerify` first (dead code after conflict detection, but keeps the resolver total), then the enable pair with `forced` captured from `forceVerify`, then the off-by-default fallthrough. The result lands in `DeepConfig.verify` (:273) and the stage machine consumes it (see `deep-think-stage-machine.md` for the confidence/close-race/force gate that `forced` feeds).
**Invariant:** expensive phases default OFF; the resolver is total over every non-conflicting flag combination (no combination reaches a missing branch); conflicts are caught by the dedicated validation step, not by resolver cleverness; the output type makes impossible states unrepresentable so downstream never re-checks flag combinations.
**Probe:** `tests/cli/resolve-verify.test.ts` (executed green at pin: 8 pass / 0 fail within the 39-test batch) — pins all five resolution arms (default off; `--verify` → `{enabled:true, forced:false}`; `--force-verify` → `{enabled:true, forced:true}`; `--no-verify` → off; both → enabled+forced) AND all three conflict arms via `detectConflicts` (verify×noVerify throws, noVerify×forceVerify throws, verify×forceVerify does NOT throw).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "resolveVerifyConfig VerifyConfig detectConflicts forceVerify noVerify", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the closed-union collapse for any tri-flag opt-in family: validate conflicts in the dedicated validation step (one error per pair, same error code), then resolve the survivors into a discriminated union where impossible states are unrepresentable. Keep the resolver total (explicit fallthrough) even for branches that conflict detection makes unreachable — it documents intent and survives refactors of the validator. Default expensive features OFF and make the forcing flag IMPLY the base flag rather than requiring both. Adapt the flag names and the error-code taxonomy to your CLI plane. Omit nothing behavioral; do not let downstream code read raw flags for this feature — only the union.
