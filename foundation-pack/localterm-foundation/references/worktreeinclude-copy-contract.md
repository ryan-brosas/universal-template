<!-- capsule-v2 -->
# .worktreeinclude copy contract — how do you make a fresh worktree immediately usable by carrying over gitignored env/secret files?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you copy exactly the untracked-and-gitignored files a repo declares (`.env`, secrets) into every new worktree — and nothing else — without ever failing the create that invited the copy?

## Patterns as pathspecs over ls-files
**Path/Symbol:** `packages/server/src/utils/copy-worktree-includes.ts:copyWorktreeIncludes` (:70–104), `parseIncludePatterns` (:22–39), `listMatchedIgnoredFiles` (:48–63), `isSafeRelativePath` (:43–46); read/write API `packages/server/src/utils/worktree-include-file.ts` (:12–28, :33–55).
**Signature:** `copyWorktreeIncludes(mainRoot: string, destPath: string): Promise<string[]>`; `writeWorktreeIncludeFile(cwd, content): Promise<WorktreeIncludeFile | null>` (empty content deletes the file).
**Data Shape:** `.worktreeignore`-syntax file at repo root; caps `MAX_WORKTREEINCLUDE_FILES=500`, `MAX_WORKTREEINCLUDE_TOTAL_BYTES=50MB`, per-file content cap 64 KiB (constants.ts:628–631). Returns relative paths actually copied.

### Decisive source
```ts
// The patterns double as git pathspecs: `git ls-files --others --ignored
// --exclude-standard -- <patterns>` lists untracked, gitignored files matching
// any pattern, which is exactly the intersection we want ("matches a pattern
// AND is gitignored"). Pathspec matching keeps huge ignored trees (node_modules)
// out of the enumeration unless a pattern names them.
const listMatchedIgnoredFiles = async (mainRoot: string, patterns: string[]): Promise<string[]> => {
  const result = await runGit(mainRoot, [
    "ls-files", "--others", "--ignored", "--exclude-standard", "-z", "--",
    ...patterns,
  ]);
  if (result.exitCode !== 0) return [];
  return result.stdout.toString("utf8").split("\0")
    .filter((rel) => rel.length > 0 && isSafeRelativePath(rel));
};
```
And the never-fail-create tail:
```ts
for (const rel of matched.slice(0, MAX_WORKTREEINCLUDE_FILES)) {
  ...
  if (totalBytes + size > MAX_WORKTREEINCLUDE_TOTAL_BYTES) break;
  try {
    fs.mkdirSync(path.dirname(dest), { recursive: true });
    fs.copyFileSync(src, dest);
    copied.push(rel);
    totalBytes += size;
  } catch {
    continue;
  }
}
```

**Flow:** parse repo-root `.worktreeinclude` (missing ⇒ []), skip blanks/comments and any `!` negation ("re-inclusion is meaningless for a copy allowlist"), strip leading slashes → one git query yields the candidate set → per-file stat guard (must be a regular file), cumulative byte cap stops early, mkdir+copy with per-file failure tolerated → caller (createGitWorktree) reports `copiedFiles` in the 201 response. The editor plane reads/writes the same file through routes GET/PUT `/api/git/worktrees/include-file`, where empty PUT content unlinks the file (revert-to-default).
**Invariant:** Copy failures are usability nuisances, never errors — git already succeeded creating the worktree, so `copyWorktreeIncludes` cannot throw and its result never fails creation. Only files git IGNORES are ever copied; tracked files stay the repo's job, so the allowlist can never duplicate tracked content.
**Probe:** `packages/server/tests/worktree-config-store.test.ts` is the config sibling; the include-copy behavior pins live in `packages/server/tests/copy-worktree-includes.test.ts` + `tests/worktree-include-file.test.ts`. Coverage caveat recorded honestly: those two fixtures spawn `git commit` WITHOUT identity env (`GIT_AUTHOR_*/GIT_COMMITTER_*` absent) and fail on this host at "unable to auto-detect email address" — the same 7 env-blocked failures triaged in pass 8's full-suite run; the seam's server-side callers are instead pinned by git-worktrees.test "baseRef head … reports no copied files without a .worktreeinclude" (:250–267, green this pass).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "copyWorktreeIncludes include patterns ignored", limit: 10 });
```
Executed live pre-write: rank rows `parseIncludePatterns` :22–39, `copyWorktreeIncludes` :70–104, `listMatchedIgnoredFiles` :48–63, `readWorktreeIncludeFile` :12–28, `writeWorktreeIncludeFile` :33–55, routes GET/PUT include-file — all line-exact; whole files then read from disk byte-for-byte.

## Verdict
Adopt the intersection trick (gitignore-syntax allowlist evaluated BY git as pathspecs over `ls-files --others --ignored --exclude-standard`), the negation-skip, the `..`/absolute segment rejection, and the never-fail-inviter rule; adapt caps to your ecosystem; omit the editor round-trip if you manage the file out-of-band. Trap: implementing the pattern matcher yourself in JS — delegating to git keeps semantics identical to what the user's own ignore rules already do, including nested `.gitignore`s via `--exclude-standard`.
