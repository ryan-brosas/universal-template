<!-- capsule-v2 -->
# Worktree list over porcelain — how does a daemon enumerate every linked worktree of a repo, with stable identity, from any worktree it happens to be asked in?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you build a complete, side-effect-free view of all worktrees (main vs linked, current, detached, locked) whose derived identity does not depend on which worktree the caller's cwd sits in?

## Porcelain parse + main-root anchoring
**Path/Symbol:** `packages/server/src/git-worktrees.ts:listGitWorktrees` (:234–261), `parseWorktreePorcelain` (:171–215), `toWorktree` (:217–232), `mainWorktreeRoot` (:142–153), `currentWorktreeRoot` (:128–133), `repoId` (:47–48), `tildifyHome` (:37–42).
**Signature:** `listGitWorktrees(cwd: string, countActiveSessions: (worktreePath: string) => number = () => 0): Promise<GitWorktreeListResponse>`; `mainWorktreeRoot(cwd): Promise<string | null>`.
**Data Shape:** Response `{ isRepo: boolean, worktrees: GitWorktree[], displayBaseDir: string | null }`; each entry `{ path (absolute), displayPath (tildified), branch (null when detached), head, isCurrent, isMain, isLocked, isPrunable, activeSessionCount }`, zod-strict in `schemas.ts:833–859`.

### Decisive source
```ts
export const mainWorktreeRoot = async (cwd: string): Promise<string | null> => {
  const result = await runGit(cwd, ["rev-parse", "--git-common-dir"]);
  if (result.exitCode !== 0) return null;
  const commonDir = result.stdout.toString("utf8").trim();
  if (!commonDir) return null;
  const root = path.dirname(path.resolve(cwd, commonDir));
  try {
    return fs.realpathSync(root);
  } catch {
    return root;
  }
};
```
And the flag projection:
```ts
isCurrent: currentRoot !== null && path.resolve(parsed.path) === path.resolve(currentRoot),
isMain: mainRoot !== null && path.resolve(parsed.path) === path.resolve(mainRoot),
branch: parsed.detached ? null : parsed.branch,
activeSessionCount: countActiveSessions(parsed.path),
```

**Flow:** non-repo short-circuits to `{isRepo:false,…}` → run `worktree list --porcelain`, `rev-parse --show-toplevel`, `rev-parse --git-common-dir` in parallel → blank-line-separated blocks parsed field-by-field (first-token split; unknown fields ignored so future git output can't break parsing; `refs/heads/` prefix stripped but raw value kept if not a ref; trailing block flushed after loop) → each entry projected with `isCurrent` (cwd's toplevel), `isMain` (common-dir parent), detached⇒null branch, and an INJECTED session count → `displayBaseDir` tildified from the read-only mirror of ensureProjectFolder (`resolveProjectFolderName`) so listing stays side-effect-free.
**Invariant:** The main root must be resolved through realpath because git prints symlink-resolved paths in porcelain — a naive `path.resolve` against a symlinked cwd mismatches every row. Anchoring project name/repo-id on the COMMON dir (not the caller's cwd) means a worktree created from inside a linked worktree still lands under its repo's own folder. Listing never mutates anything.
**Probe:** `packages/server/tests/git-worktrees.test.ts` — "reports a non-repo directory" :72–83; "lists the main worktree, marks it current and main, reports tildified base dir" :85–114 (exact whole-row equality incl. `activeSessionCount: 0`); "lists added worktrees: main flagged, linked not main, detached/locked" :116–158 (detached ⇒ branch null, lock flag survives). Executed this pass: suite 13/13 green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "worktree config store sweep", limit: 10 });
```
Executed live pre-write: rank#1–11 return `worktreeConfigPathFor`, `configPathFor`, `toWire`, `WorktreeConfigStore.*`, `sweepStaleWorktrees`, `parseWorktreePorcelain` (:171–215), `listGitWorktrees` (:234–261), `toWorktree` (:217–232), `mainWorktreeRoot` (:142–153) with line-exact ranges; `get_code_snippet(parseWorktreePorcelain/listGitWorktrees)` returned source byte-equal to disk.

## Verdict
Adopt the shape: porcelain block parser tolerant of unknown fields, main-root anchoring via `--git-common-dir`+realpath, injected per-path occupancy callback instead of a service dependency; adapt the state-dir layout (`~/.localterm/worktrees/<project>`) and hash lengths (repo-id 12 hex, folder suffix 6) to your host; omit the display-only `displayBaseDir` mirror if your client resolves home itself. Trap: comparing un-resolved paths against porcelain output silently drops rows on macOS where `/tmp` is `/private/tmp`.
