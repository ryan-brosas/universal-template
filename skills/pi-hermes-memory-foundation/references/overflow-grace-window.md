<!-- capsule-v2 -->
# Overflow grace window — stamp first-overflow, defer auto-consolidation N ms, clear on any successful manual mutation

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** Auto-consolidation fires the moment memory overflows — but the model holding the "memory full" error should get one chance to consolidate MANUALLY in the same turn. How do you delay the automatic path without losing it?

## MemoryStore overflow grace
**Path/Symbol:** `src/store/memory-store.ts` — field `overflowSince` (:63), `overflowGraceMs()` (:131–136, `Number.isFinite && >= 0` else `DEFAULT_OVERFLOW_GRACE_MS = 180000` from constants :38–39), `clearOverflow` (:138–140), `overflowGraceActive` (:142–145); stamping at `_add` :236 (`this.overflowSince[target] ??= Date.now()`); deferral append in `add` :277–282; clearing in `runTargetMutation` :853; config plumbing `src/config.ts` (:57 default, :117 `isNonNegativeNumber` gate) + `src/types.ts:overflowGraceMs`.
**Signature:** per-target state keyed `"memory" | "user" | "failure"`; `runTargetMutation(target, mutation: (markMutation: () => void) => Promise<MemoryResult>)` — every mutating path (add/replace/remove/applyMutationPlan) now receives and calls `markMutation()`.
**Data Shape:** `MemoryResult.error` gains a suffix when grace is active: `"… Automatic consolidation is deferred for ${graceMs}ms after overflow so you can consolidate '${target}' manually first — retry after the grace window."`

### Decisive source
```ts
// _add: FIRST overflow stamps the clock — later overflowing adds never restart it:
this.overflowSince[target] ??= Date.now();

// add(): strategy === "auto-consolidate" and consolidation failed/deferred:
if (this.overflowGraceActive(target)) {
  return { ...result,
    error: `${result.error} Automatic consolidation is deferred for ${this.overflowGraceMs()}ms …` };
}

// runTargetMutation: ANY successful write that actually mutated clears the window:
if (result.success && mutated) this.clearOverflow(target);
```

**Flow:** add overflows → stamp `overflowSince[target]` once → consolidator invoked (or deferred by lock) → if it did not free space, the error is augmented with the manual-first instruction while `Date.now() - since < graceMs` → after 180 s the next overflowing add runs consolidation again → a successful MANUAL replace/remove/plan write (any `markMutation()` call that reaches success) clears the stamp so the model's own cleanup resets the clock.
**Invariant:** the grace is PER-TARGET, starts at the FIRST overflow, and is never restarted by duplicate failing adds — otherwise an agent retrying a rejected add every turn would postpone auto-consolidation forever. Only a successful MUTATING operation clears it (a failed or no-op write must not). FIFO-evict adds also route through `markMutation()` on success (:241). Default 180 s ≈ the consolidation timeout budget — long enough for one manual turn, short enough that automation resumes.
**Probe:** `npx tsx --test tests/store/memory-store.test.ts` — "defers auto-consolidation during the per-target overflow grace window" (:207, two overflowing adds ⇒ `consolidatorCalls === 0`, both errors match `/deferred/`), "runs auto-consolidation after the original overflow grace expires" (:232, mocked `Date.now` +60_001 ⇒ exactly 1 consolidator call), "does not restart expired overflow grace after a duplicate add" (:261, successful re-add of an existing entry then overflow ⇒ still exactly 1 call), "clears overflow grace after a successful manual write" (:291, replace then overflow ⇒ 0 consolidator calls). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "overflowSince overflowGraceMs clearOverflow markMutation", limit: 5 })`

## Verdict
Adopt first-overflow stamping + success-mutation clearing around any automatic recovery loop. Adapt the grace duration and the error copy. Pair with `consolidation-lock-ladder.md` (the deferred-not-failed outcome this builds on) and `memory-full-error-entries.md` (what the model sees alongside the deferral note).
