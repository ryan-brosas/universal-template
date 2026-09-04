<!-- capsule-v2 -->
# Git canonical root — how do you find a repo's true root from any subdirectory or linked worktree?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Why does naive `.git`-stripping break in subdirs and worktrees, and what's the fix?

## git-common-dir + realpath join
**Path/Symbol:** `src/git/git_context.c:cbm_git_context_resolve` + reproduce-first tests tests/test_git_context.c:101–163.
**Signature:** `int cbm_git_context_resolve(const char *path, cbm_git_context_t *ctx);`
**Data Shape:** ctx.canonical_root = realpath of the repository root; works when invoked from the root, from a SUBDIRECTORY, and from a linked worktree (`.git` is a FILE pointing at gitdir there, not a directory).

### Decisive source
```c
/* THE reproduce-first guard: from a subdir, --git-common-dir is relative, so the
 * unfixed derive_canonical_root joins it against worktree_root and strips "/.git"
 * textually, leaving canonical_root = "<root>/subdir/.." (or "<root>/..") instead
 * of "<root>". Verified RED on the unfixed code, GREEN with the realpath fix. */
TEST(canonical_root_subdir) { ... ASSERT_STR_EQ(ctx.canonical_root, expected); }
```

**Flow:** locate enclosing repo (`git -C <dir> rev-parse`) → resolve common dir → join/normalize against the WORKTREE root (not the invocation dir) → strip `.git` component → realpath the result so symlinks and `..` collapse to one canonical identity used for cache keys and project naming.
**Invariant:** Never textual-strip ".git" off a joined path — resolve then realpath; the same canonical root must result regardless of which subdir the tool ran in.
**Probe:** `tests/test_git_context.c:canonical_root_repo_root`, `canonical_root_subdir`, `canonical_root_linked_worktree`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_git_context_resolve", limit: 5 });
```

## Verdict
Adopt resolve-then-realpath for repo identity; adapt to your git plumbing availability; omit worktree handling only if your indexer never sees them (it usually does).
