<!-- capsule-v2 -->
# Worktree auto-detect + create — how does a session find its isolated checkout after a restart?

**Source:** pi-autoresearch-harness MIT `main@511760df8905c7b6e6bbd3a028de734becff69e6`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness`. **Question:** How is the right worktree identified among many, and what makes creation idempotent?

## detectAutoresearchWorktree / createAutoresearchWorktree — porcelain walk + canonical-path compare
**Path/Symbol:** extension copy `extensions/pi-autoresearch/src/git/index.ts` — detect :99–120, display :123–130, create :137–196, remove :201–231; server twins `harness/server.ts:481–500 / 502–559 / 561–588`; gitignore guard :431–474.
**Signature:** `detectAutoresearchWorktree(ctxCwd, sessionId?): string | null`; `createAutoresearchWorktree(ctxCwd, sessionId): string | null`.
**Data Shape:** worktree layout `<repo>/autoresearch/<sessionId>/` on branch `autoresearch/<sessionId>`; marker = presence of `autoresearch.jsonl` inside the worktree.

### Decisive source
```ts
const output = execFileSync('git', ['worktree', 'list', '--porcelain'], { cwd: ctxCwd, ... });
for (const worktreePath of worktreePaths(output)) {          // lines starting "worktree "
  if (sessionId) {
    const expectedSuffix = normalizePath(join('autoresearch', sessionId));
    if (!canonicalPath(worktreePath).endsWith(expectedSuffix)) continue;  // session filter
  }
  const jsonlPath = join(worktreePath, 'autoresearch.jsonl');
  if (fs.existsSync(jsonlPath)) return worktreePath;         // jsonl = live-session marker
}
```

**Flow:** session_start/activate → if no runtime.worktreeDir → detect: parse `worktree list --porcelain`, canonicalize each path (`realpathSync.native`, fallback resolve; backslashes normalized; lowercased on win32), require suffix `autoresearch/<id>` AND existing JSONL. Not found → create: skip if canonical-equal entry already registered (idempotent re-entry), `worktree prune` stale rows, mkdir `autoresearch/`, create branch ONLY if absent, `worktree add <path> <branch>`, then `ensureGlobalGitignore()` — appends `autoresearch/` to the user's GLOBAL excludesfile (core.excludesfile → ~/.gitignore → ~/.gitignore_global → ~/.config/git/ignore) only when no line equals exactly `autoresearch/`.
**Invariant:** detection keys on the JSONL FILE, not directory existence — a pruned/cleaned worktree without state is invisible. Canonical-path comparison (not string equality) is what survives symlinked TMPDIRs and case-insensitive filesystems. Global (not repo) gitignore keeps the host repo clean of autoresearch artifacts WITHOUT touching tracked files.
**Probe:** direct tests `__tests__/unit/jsonl.test.ts:11–118` (detect: none/matching/wrong-session/two-session/no-jsonl cases) + `__tests__/integration/worktree.test.ts` + `__tests__/integration/session-isolation.test.ts` describe('detectAutoresearchWorktree session filtering'); anchors `grep -n "'worktree', 'add'" harness/server.ts extensions/pi-autoresearch/src/git/index.ts` → server :549, ext :185; `grep -n 'ensureGlobalGitignore()' harness/server.ts` → :454 def + :554 call.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-autoresearch-harness", query: "detectAutoresearchWorktree worktree list porcelain ensureGlobalGitignore", limit: 10 });
```

## Verdict
Adopt porcelain-walk detection with canonical-path+jsonl-marker identity verbatim; adapt the global-ignore mechanism to hosts without git (plain directory isolation); omit the branch-per-session scheme only if you don't need merge-back. Direct tests cover the detection matrix thoroughly.
