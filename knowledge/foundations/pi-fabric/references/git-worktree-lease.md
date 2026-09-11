<!-- capsule-v2 -->
# Git worktree lease — how do you give a sub-agent an isolated checkout and guarantee cleanup?

**Source:** pi-fabric (MIT), `feat/veda-runner@4874ac3a`; Codebase Memory `pi-fabric`. **Question:** How does the agent manager isolate concurrent agents on one repo using git worktrees?

## Git worktree lease
**Path/Symbol:** `src/agents/worktree-manager.ts:WorktreeManager.create/cleanup/get` (:22–61); consumer `src/agents/manager.ts:327` (`readonly #worktrees = new WorktreeManager()`).
**Signature:** `create(id, cwd, name): Promise<{gitRoot, path, branch}>`; `cleanup(id, deleteBranch = false): Promise<boolean>` (false when no lease).
**Data Shape:** branch name `pi-fabric/<safeLabel(name)>-<id.slice(0,8)>` where safeLabel lowercases, collapses non-`[a-z0-9-]` runs to `-`, trims dashes, caps 30 chars, falls back to `"agent"`; worktrees rooted at `os.tmpdir()/pi-fabric-worktrees/<id>`.

### Decisive source
```ts
gitRoot = (await executeFile("git", ["rev-parse", "--show-toplevel"], { cwd })).stdout.trim();
...
await executeFile("git", ["worktree", "add", "-b", branch, worktreePath, "HEAD"], {
      cwd: gitRoot, timeoutMs: 60_000,
});
```

**Flow:** create resolves the repo toplevel from the REQUEST cwd (throws `"Worktree isolation requires a Git repository"` when absent) → mints branch + tmpdir path → `git worktree add -b <branch> <path> HEAD` (60s timeout) → lease cached by agent id. cleanup: `git worktree remove --force` (60s) → optional `git branch -D` (30s) → map delete.
**Invariant:** The lease map is the single source of truth — cleanup is inert (returns false) for unknown ids, so double-cleanup is safe; branch is derived from NAME+id-prefix so it's human-readable yet collision-resistant per run; every git call carries an explicit timeoutMs (a hung git must not wedge the manager); isolation is from HEAD at creation time — the parent never rebases the child mid-run.
**Probe:** `grep -c 'pi-fabric-worktrees' src/agents/worktree-manager.ts` → 1; `grep -c '"worktree", "add", "-b"' src/agents/worktree-manager.ts` → 1. No dedicated upstream test file for this module (coverage caveat: exercised via agents/manager integration paths — behavior pinned from source).
**Anchor:** repo root.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "WorktreeManager create cleanup lease worktree branch", limit: 10 });
// WorktreeManager.cleanup Method src/agents/worktree-manager.ts 46-61
```

## Verdict
Adopt the id-keyed lease + timeout-per-git-call pattern for any multi-agent checkout isolation; adapt the branch naming scheme to your conventions; omit force-remove if you need to preserve uncommitted child work (then surface it instead of deleting).
