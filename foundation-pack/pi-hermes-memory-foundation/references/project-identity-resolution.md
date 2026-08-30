<!-- capsule-v2 -->
# Project identity resolution — git-worktree-shared repo-root detection with legacy-name migration bridge

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** Project-scoped memory keyed on the cwd basename strands every git worktree in its own silo (#120) — how do you resolve ONE shared identity per repository without spawning git, while never orphaning memory already written under old names?

## detectProject + findGitRepoRoot
**Path/Symbol:** `src/project.ts:detectProject` (:99–123), `resolveProjectName` (:125–149), `findGitRepoRoot` (:32–56), `resolveWorktreeCommonDir` (:58–80), `repoRootCache` (:82); consumers `detectProjectSkills` (:151–157).
**Signature:** `detectProject(projectsMemoryDir = "projects-memory", cwd?) → { name: string | null, memoryDir: string | null }`.
**Data Shape:** project memory lives at `~/.pi/agent/projects-memory/<name>/`; `name = null` means "not in a project" (home dir, `/`, or empty basename).

### Decisive source
```ts
// Mirrors what `git rev-parse --git-common-dir` reports, without spawning git:
// a linked worktree's `.git` is a file pointing at
// <main>/.git/worktrees/<name>, and that directory carries a `commondir`
// file pointing back at the shared <main>/.git.
function findGitRepoRoot(dir: string): string | null {
  let current = path.resolve(dir);
  while (true) {
    const dotGit = path.join(current, ".git");
    const stat = fs.statSync(dotGit) /* try/catch */;
    if (stat?.isDirectory()) return current;              // plain repo root
    if (stat?.isFile()) {
      const commonDir = resolveWorktreeCommonDir(current, dotGit);
      if (!commonDir) return current;
      return path.basename(commonDir) === ".git" ? path.dirname(commonDir) : commonDir;
    }
    const parent = path.dirname(current);
    if (parent === current) return null;
    current = parent;
  }
}

// Inside a Git repository the project name is the REPOSITORY root's basename,
// so every linked worktree shares one identity instead of stranding its memory
// and skills under the worktree directory name (#120).
function resolveProjectName(resolved, resolvedHome, cwdName, projectsRoot): string {
  // cached findGitRepoRoot …
  if (!repoRoot || repoRoot === resolved || repoRoot === resolvedHome) return cwdName;
  const repoName = path.basename(repoRoot);
  if (!repoName || repoName === cwdName) return cwdName;

  // Migration bridge: a store already written under the old cwd-basename
  // identity keeps working. Only fresh directories adopt the repository name.
  if (!fs.existsSync(path.join(projectsRoot, repoName))
      && fs.existsSync(path.join(projectsRoot, cwdName))) {
    return cwdName;
  }
  return repoName;
}
```

**Flow:** (1) reject non-project cwds (home, `/`) up front; (2) walk upward reading `.git` entries — directory ⇒ done, file ⇒ read its `gitdir:` pointer, then that dir's `commondir` file to reach the SHARED `.git` (with a two-levels-up fallback for older layouts missing a commdir file); results are memoized in a module Map keyed by resolved cwd; (3) name = repo-root basename unless equal to the cwd basename or absent; (4) the migration bridge keeps an existing `<cwdName>` store authoritative when no `<repoName>` store exists yet.
**Invariant:** identity changes must NEVER strand data — the bridge means upgrading from cwd-keyed to repo-keyed naming is invisible for existing users and applies only to new projects; the walk never shells out to git (works where git is unavailable or slow); results are cached because this runs on every session start. A worktree and its main checkout share skills AND memory by construction.
**Probe:** `tests/project.test.ts` (worktree common-dir resolution incl. the `commondir`-less fallback), `tests/project-rebinding.test.ts` (project switch rebinds stores mid-session). Coverage caveat: tests/ excluded from the graph index.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "detectProject findGitRepoRoot resolveWorktreeCommonDir", limit: 5 })`

## Verdict
Adopt the pure-filesystem repo-root walk plus the existence-check migration bridge whenever scoping per-project state. Adapt the storage root and the "what counts as not-a-project" set. Pair with `legacy-layout-migration.md` for the one-time folder moves.
