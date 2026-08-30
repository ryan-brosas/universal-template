<!-- capsule-v2 -->
# Shadow-git checkpoints — what must a porter validate BEFORE any snapshot op, and why does every git call run in a sanitized environment?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** A porter wants per-task undo — where do snapshots live, what is validated at init vs discovered missing at first restore, and what does the shadow-git indirection actually protect?

## One shadow repo per task; init-time validation ladder; sanitized env on EVERY git call
**Path/Symbol:** `src/services/checkpoints/ShadowCheckpointService.ts` — `createSanitizedGit` :27-77 (7-var env scrub), constructor protected-paths guard :108-127, `initShadowGit` validation ladder :129-207, `writeExcludeFile` :214-218 (`excludes.ts` `getExcludePatterns` :201-212), nested-git ripgrep probe :230-279, `saveCheckpoint` no-change push :295-342, `restoreCheckpoint` clean-before-reset :344-372, `getDiff` root-rev fallback :374-406, static layouts :432-448, `deleteTask`/`deleteBranch` worktree-unset dance :450-516; `RepoPerTaskCheckpointService.create` :6-15; Task-side lifecycle `src/core/checkpoints/index.ts` `getCheckpointService` :27-129.
**Signature:** `initShadowGit(onInit?) → {created, duration}`; `saveCheckpoint(message, {allowEmpty?, suppressMessage?}) → CheckpointResult | undefined` (undefined = nothing to commit); `restoreCheckpoint(commitHash)`; `getDiff({from?, to?})`; `static hashWorkspaceDir(dir) → 8-hex-slice`.
**Data Shape:** TWO layouts coexist at this pin: task repo `<globalStorageDir>/tasks/<taskId>/checkpoints` (the one Task.ts uses) and workspace repo `<globalStorageDir>/checkpoints/<sha256(workspaceDir)[:8]>` (:447) whose only remaining consumer is static `deleteTask`. Shadow config: `core.worktree=<workspaceDir>`, `commit.gpgSign=false`, fixed identity `Roo Code <noreply@example.com>`; excludes live in `.git/info/exclude` (shadow-local).

### Decisive source
```ts
// :36-44 — inherited git env vars would silently REDIRECT shadow ops at the
// user's own repository; all seven are stripped before any git call:
if (key === "GIT_DIR" || key === "GIT_WORK_TREE" || key === "GIT_INDEX_FILE" ||
    key === "GIT_OBJECT_DIRECTORY" ||
    key === "GIT_ALTERNATE_OBJECT_DIRECTORIES" ||
    key === "GIT_CEILING_DIRECTORIES" || key === "GIT_TEMPLATE_DIR") { removedVars.push(...); continue }
// :156-170 — reattach validation happens at INIT, not first restore:
if (await fileExistsAtPath(this.dotGitDir)) {
    const worktree = await this.getShadowGitConfigWorktree(git)
    if (!worktree) throw new Error("Checkpoints require core.worktree to be set in the shadow git config")
    if (!arePathsEqual(worktree.trim(), this.workspaceDir))
        throw new Error(`Checkpoints can only be used in the original workspace: ${worktreeTrimmed} !== ${this.workspaceDir}`)
}
// :176-183 — fresh repo: template-less init so hooks/samples never leak in
await git.init({ "--template": "" })
await git.addConfig("core.worktree", this.workspaceDir)
```

**Flow:** task start → `getCheckpointService(task)` ladders through enableCheckpoints/existing-service/init-in-progress latch with pWaitFor (WARNING_THRESHOLD_MS=5000 warn, timeout ⇒ disable + undefined) → `RepoPerTaskCheckpointService.create` → `initShadowGit`: nested-git ripgrep probe (`-g '**/.git/HEAD'`, root `.git/HEAD` excluded :248, probe FAILURE = feature proceeds fail-open :271-278) → mkdir → existing repo? validate core.worktree present AND equal to this workspace, else throw → fresh? template-less init + configs + excludes + stageAll(swallow-errors) + empty initial commit = baseHash → emit initialize. Save = stageAll → commit (allowEmpty opt) → **push toHash EVEN when result.commit is falsy** (:314) but only emit/return on real commit — duplicate saves stay addressable without ghost events. Restore = `clean(f,[–d,-f])` BEFORE `reset(--hard,hash)` (untracked files can block reset), then truncate `_checkpoints` to include the restored hash. Diff without from = rev-list `--max-parents=0` root commit (:382), stages untracked first so they appear, after-content reads WORKTREE file when to omitted. Task deletion deletes branch `roo-<taskId>` in the WORKSPACE repo by temporarily UNSETTING core.worktree so checkout/reset cannot touch the user's tree, then restores it in finally (:507-511).
**Invariant:** The shadow repo and the user's repository must never share object databases or refs — enforced negatively (env scrub) rather than by isolation guarantees, because any single inherited GIT_* var redirects every subsequent git call at the wrong repo. All dangerous validation (worktree set + matches workspace, protected paths homedir/Desktop/Documents/Downloads :115-118) fails LOUDLY at init; restore safety depends on it having happened. Nested repos DISABLE checkpoints entirely (a shadow commit inside a nested repo would capture the wrong tree); the ripgrep check failing open is deliberate availability-over-correctness. Excludes are shadow-local `.git/info/exclude` — user .gitignore is respected implicitly by git plus ~200 patterns across 8 families (+ LFS paths parsed from workspace `.gitattributes` filter=lfs lines).
**Probe:** deterministic probes (byte-exact from repo root):
`grep -o '"GIT_[A-Z_]*"' src/services/checkpoints/ShadowCheckpointService.ts | wc -l` = **7**
`grep -n 'Cannot use checkpoints in' src/services/checkpoints/ShadowCheckpointService.ts` → **:118** only
`grep -n 'require core.worktree' src/services/checkpoints/ShadowCheckpointService.ts` → **:161**
`grep -c 'arePathsEqual' src/services/checkpoints/ShadowCheckpointService.ts` = **2** (import :12 + guard call)
`grep -n -- '--template' src/services/checkpoints/ShadowCheckpointService.ts` → **:176** (the `--` guard is REQUIRED — `-F '--template'` dies on "unrecognized option"; verified live)
`grep -n -e '--unset' src/services/checkpoints/ShadowCheckpointService.ts` → **:485** (deleteBranch worktree unset)
`grep -n 'max-parents=0' src/services/checkpoints/ShadowCheckpointService.ts` → **:382**
`grep -n '\*\*/\.git/HEAD' src/services/checkpoints/ShadowCheckpointService.ts` → **:233** (nested probe)
Direct tests pin the TASK-LIFECYCLE side only: `src/core/checkpoints/__tests__/checkpoint.test.ts` (25 its — init-wait latch :109, timeout-disable :138/:493, save-waits-for-init :109, restore-on-delete/edit :217/:233, diff modes :300/:326/:351, WARNING_THRESHOLD_MS=5000 pinned by name :551). No dedicated suite exercises the ShadowCheckpointService git mechanics themselves at this HEAD — coverage caveat stands.
**Retrieve:** `search_graph` project Roo-Code, query `"ShadowCheckpointService initShadowGit core.worktree"` → rank#1 Method `initShadowGit` :129-207 line-exact (total 1104; also surfaces `getShadowGitConfigWorktree` :281-293). Note unrelated `packages/core/src/worktree/worktree-service.ts` WorktreeService rows pollute lower ranks — route by Source path, not name similarity.

## Verdict
Adopt per-task shadow repos with init-time validation ladder + env-sanitized git. Adapt layout paths and identity config to your host; keep clean-before-reset ordering and the deleteBranch worktree-unset-finally dance verbatim. Omit getDiff UI plumbing if you have no viewer. Coverage caveat: lifecycle side test-pinned via checkpoint.test.ts; git-mechanics side verified by source reading only at this pin. Cross-reference opencode-foundation/references/snapshot.md for shared object-store tricks.
