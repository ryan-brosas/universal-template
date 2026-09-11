<!-- capsule-v2 -->
# Checkpoint conflict gate — how does a CLI handler arbitrate resume vs fresh-start vs conflicting checkpoint?

**Source:** Veda (`veda-ts`, MIT, `master@c3c69f2c340ec81ada8ea974076ce5bbaf5ccbc6`); Codebase Memory `veda`. **Question:** A resumable pipeline persists a checkpoint at every stage boundary. When the command starts and a checkpoint already exists, what are the exact arms — and what does each arm do to the stored state?

## Three arms: resume-validate, force-clear, loud-exit
**Path/Symbol:** `src/commands/deep.ts:handleDeep` checkpoint gate (:187-246); store surface `src/checkpoint/store.ts:CheckpointStore` (`load`/`save`/`clear`/`getSummary`); identity validation via `computeRunIdentityHash` (see run-identity-hash capsule).
**Signature:** gate runs before any pipeline spend: `const existingCheckpoint = await checkpointStore.load(); if (existingCheckpoint) { ... }`.
**Data Shape:** the checkpoint carries `checkpoint_version: 1`, `runIdentityHash`, embedded `trace`, `status: 'partial' | 'complete'`, `completedStage`, `failedStage?`, `error?`, `timestamp`, `successfulCandidateIds`, judge resume state (`judgeSeed`, `judgeIndexMapping`, `judgeSelectedIndex`, `judgeSelectedDisplayIndex`, `selectedCandidateId`), verify resume state (`verifyChecks`, `partialVerifyResults`), and `usageAtCheckpoint`.

### Decisive source
```ts
if (existingCheckpoint) {
  if (options.resume) {
    // Validate run identity (unless --force-resume)
    const currentIdentity = computeRunIdentityHash({ prompt, context, options: {...} });
    if (existingCheckpoint.runIdentityHash !== currentIdentity && !options.forceResume) {
      console.error(`[error] Checkpoint run identity mismatch.`);
      console.error(`  Use --force-resume to resume anyway, or --force to start fresh.`);
      process.exit(1);
    }
    // Resume from checkpoint - will be passed to runDeepThink below
    // Don't clear - we'll use the checkpoint data
  } else if (options.force) {
    // Clear and start fresh
    await checkpointStore.clear();
  } else {
    // Error with helpful message
    const summary = await checkpointStore.getSummary();
    console.error(`[error] Checkpoint exists from previous run.`);
    console.error(`  Stage: ${summary?.completedStage} → ${summary?.failedStage ?? 'complete'}`);
    console.error(`  Use --resume to continue from checkpoint`);
    console.error(`  Use --force to start fresh (overwrites checkpoint)`);
    process.exit(1);
  }
}
```
**Flow:** no checkpoint ⇒ fall through and run fresh → `--resume` ⇒ validate identity (mismatch exits loudly unless `--force-resume`), then pass the stored trace/stage/judge/verify state into `runDeepThink` as `resumeCheckpoint` — the stored checkpoint is NOT cleared here → `--force` ⇒ `checkpointStore.clear()` then fresh run → neither flag ⇒ print a human summary (stage progression, candidate count, timestamp) and exit 1 with both escape hatches named → on SUCCESS the handler clears the checkpoint (`if (finalResult) await checkpointStore.clear()`); on failure the pipeline's onCheckpoint hook has already persisted the latest state.
**Invariant:** the handler never clears a checkpoint it might resume from; clearing happens only on explicit `--force` or on a completed run; the gate runs BEFORE any model spend, so a conflicting checkpoint costs zero tokens.
**Probe:** `tests/pipelines/deep-resume.test.ts` (executed live at pin: 10 pass / 0 fail) pins the resume path; `tests/commands/deep.test.ts` (same run: 32 pass / 0 fail across both files) pins the ad-hoc context that feeds identity. The three-arm gate itself is CLI-glue with no dedicated upstream test — source-pinned probe: `grep -n "force-resume\|Overwriting existing checkpoint\|Checkpoint exists from previous run" src/commands/deep.ts` → the three arms at :206/:231/:237.
**Coverage caveat:** `process.exit(1)` inside a command handler is fine for a CLI but a library port should throw a typed error instead.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "veda", query: "handleDeep checkpoint exists resume force clear getSummary", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-arm gate with zero-spend conflict detection, human-readable checkpoint summaries, and success-time clearing. Adapt the exit mechanism (exit(1) → typed error) for library use. Omit the judge/verify sub-state fields if your pipeline has no mid-stage resume.
