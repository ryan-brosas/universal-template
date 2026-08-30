<!-- capsule-v2 -->
# Stale-worktree sweep — how do you garbage-collect auto-created worktrees so no run can ever destroy user work?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you delete old worktrees from a shared directory while guaranteeing that manual worktrees, dirty trees, occupied shells, and unpushed commits all survive?

## Eligibility funnel + double-gated cleanliness
**Path/Symbol:** `packages/server/src/utils/worktree-sweep.ts:sweepStaleWorktrees` (:66–104), `isAutoCreated` (:21–24), `isClean` (:26–30), `worktreeAgeMs` (:32–39), `reapEmptyProjectFolder` (:47–58).
**Signature:** `sweepStaleWorktrees(cwd: string, now: number = Date.now(), isWorktreeBusy: (worktreePath: string) => boolean = () => false): Promise<{ removed: string[] }>`.
**Data Shape:** Eligibility inputs per worktree: path, isMain/isCurrent flags (from the list capsule), directory mtime; constants `WORKTREE_SWEEP_MAX_AGE_DAYS=30`, `WORKTREE_SWEEP_BATCH_LIMIT=100` (constants.ts:637–638); result lists only paths actually removed.

### Decisive source
```ts
for (const worktree of worktrees) {
  if (removed.length >= WORKTREE_SWEEP_BATCH_LIMIT) break;
  if (worktree.isMain || worktree.isCurrent) continue;
  if (!isAutoCreated(worktree.path)) continue;

  const age = worktreeAgeMs(worktree.path, now);
  if (age === null || age < cutoff) continue;

  // A shell still sitting in a stale worktree blocks the sweep too — same
  // reason as the delete route. Checked before the git cleanliness spawn
  // since it's an in-memory lookup.
  if (isWorktreeBusy(worktree.path)) continue;

  if (!(await isClean(worktree.path))) continue;

  const result = await runGit(cwd, ["worktree", "remove", worktree.path]);
  if (result.exitCode === 0) {
    removed.push(worktree.path);
    reapEmptyProjectFolder(worktree.path);
  }
}
```
The comment that pins the safety argument:
```ts
// A worktree is sweepable iff it is auto-created (lives under the shared
// ~/.localterm/worktrees dir, so a worktree the user made manually elsewhere is
// never touched), is older than the cutoff, and is clean — no uncommitted
// changes and no untracked files. `git worktree remove` (without --force)
// double-gates cleanliness: git itself refuses a dirty worktree, so a clean
// check that raced with a concurrent edit still can't lose work. The branch
// ref is left behind by `worktree remove`, so even a swept worktree with
// unpushed commits is recoverable via `git worktree add <path> <branch>`.
```

**Flow:** list via the porcelain service (list failure ⇒ `{removed:[]}`, never throws) → per entry: batch cap → main/current exempt → prefix-containment under the state worktrees dir only → mtime age ≥ 30d → injected busy predicate (PTY occupancy) BEFORE spawning git → `status --porcelain -uall` empty → `git worktree remove` (no --force) → on success reap the project folder ONLY when its every remaining entry is the repo-id marker.
**Invariant:** The sweep never throws and never enumerates skips — callers just see fewer removals, so a sweep triggered from the list view can't break that view. Cleanliness is checked twice (own porcelain read AND git's own refusal) to close the race against a concurrent edit. Folder reaping is conservative: any sibling worktree or user file keeps the folder.
**Probe:** `packages/server/tests/worktree-sweep.test.ts` — removes stale+clean+auto-created :58–76; keeps dirty :78–96; keeps recent :98–116; busy predicate blocks even stale+clean :118–138; reaps emptied project folder :140–156; keeps folder when a sibling stays :158–176. Executed this pass: 6/6 green.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "worktree config store sweep", limit: 10 });
```
Executed live pre-write: `sweepStaleWorktrees` :66–104 ranked with helpers `worktreeAgeMs` :32–39, `isClean` :26–30, `isAutoCreated` :21–24, `reapEmptyProjectFolder` :47–58; `trace_path(sweepStaleWorktrees, inbound)` → hop1 `buildApiRoutes`, hop2 `createServer`.

## Verdict
Adopt the funnel order (cheap in-memory checks before spawns; batch cap first), the double-gated clean check, and marker-guarded folder reaping; adapt the age threshold and batch size; omit the auto-created prefix gate only if your tool owns the whole directory. Trap: sweeping by mtime alone — here mtime is merely one AND-clause; deleting anything with unpushed commits is prevented structurally because branch refs survive `worktree remove` and the tool never passes --force.
