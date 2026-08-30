<!-- capsule-v2 -->
# Memory mutation plan — validate the whole operation list against an unpublished draft, then commit once; size gates and requireShrink are part of validation, not cleanup

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** An LLM hands you a LIST of memory edits (add/replace/remove) to apply atomically — how do you guarantee all-or-nothing semantics when each edit individually would pass?

## MemoryStore.applyMutationPlan
**Path/Symbol:** `src/store/memory-store.ts:applyMutationPlan` (:327–411) under `runTargetMutation` (the markdown-mutation-lock.md mutex); per-op validation loop (:344–384); publish gates (:385–401); `buildFailureMemoryText` call site inside failure adds (:355–360; builder defined :590); `areDistinctScopedFailureCopies` (:580–588).
**Signature:** `applyMutationPlan(target, operations: {action:"add"|"replace"|"remove", content?, oldText?, category?, failureReason?, project?}[], options?: {requireShrink?: boolean}) → Promise<MemoryResult>`.
**Data Shape:** `plannedEntries: string[]` — the encoded-entry draft mutated across the loop; `originalTotal/plannedTotal` = joined delimiter length compared against `this.charLimit(target)`.

### Decisive source
```ts
if (operation.action === "add") {
  ...
  if (plannedEntries.some((entry) => {
    const decoded = this.decodeEntry(entry);
    return decoded.text === normalizedContent
      && (target !== "failure" || decoded.project === normalizedProject);
  })) return { success: false, error: "Memory mutation plan would add a duplicate entry." };
}
...
if (plannedTotal > this.charLimit(target)) {
  return { success: false, error: `Memory mutation plan would put memory at ${plannedTotal}/${this.charLimit(target)} chars.` };
}
if (options.requireShrink && plannedTotal >= originalTotal) {
  return { success: false, error: `Memory mutation plan did not shrink the target (${originalTotal} -> ${plannedTotal} chars).` };
}
this.setEntries(target, plannedEntries);   // FIRST AND ONLY publish
await this.saveToDisk(target);
```
Later ops see EARLIER ops' effects (an add is matchable by a subsequent remove) because they mutate the shared draft; duplicate detection therefore checks the draft, not the original list. Failure adds default their category to "failure" and stamp project at plan time (`applyReviewOperations` :309–316 feeds this).

**Flow:** lock → snapshot original → run every op against the draft with immediate typed-error returns → size/shrink gates on the final draft → single `setEntries` + disk write. Any rejection leaves `memoryEntries` untouched (tests assert raw file bytes unchanged after failed plans).
**Invariant:** nothing is written until EVERY op validates against the post-predecessor state — a porter who applies ops one-by-one with a rollback handler gets a different (worse) contract: intermediate states are observable to concurrent readers of `getEntries`, and a crash mid-list persists half the plan. `requireShrink` is enforced on PLAN SIZE not per-op, so a replace that grows is legal if the whole plan still shrinks.
**Probe:** `tests/store/memory-store.test.ts` — "rejects invalid plans before publishing any draft" (:981, six-case error matrix incl. `/duplicate entry/` and byte-identical file assertions), "requires a strictly smaller final plan" (:1085), "replaces identical failure text across project scopes while preserving each scope" (:510).
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "applyMutationPlan plannedEntries requireShrink charLimit", limit: 5 })`

## Verdict
Adopt for any LLM-authored batch edit over a human-readable store. Adapt op verbs and limits; keep draft-validate-commit-once, draft-scoped duplicate detection, and plan-level shrink gating. Omit nothing.
