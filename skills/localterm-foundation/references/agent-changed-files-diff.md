<!-- capsule-v2 -->
# changedFiles diff synthesis — how do you report what an agent run actually touched?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you derive a run's file impact without instrumenting the agent?

## git status --porcelain set difference before/after, sorted, capped
**Path/Symbol:** `packages/server/src/agent-git-status.ts:gitStatusSet` (:19–30) + `computeChangedFiles` (:32–39).
**Signature:** `computeChangedFiles(before: Set<string>, cwd: string): string[]`.
**Data Shape:** Porcelain lines sliced at :3 (`XY <path>`), rename arrows resolved to the POST-rename side (`old -> new` keeps new), quoted paths unquoted; output capped at `MAX_AUTOMATION_CHANGED_FILES = 64`, sorted lexicographically.

### Decisive source
```ts
const after = gitStatusSet(cwd);
  const changed: string[] = [];
  for (const filePath of after) if (!before.has(filePath)) changed.push(filePath);
  for (const filePath of before) if (!after.has(filePath)) changed.push(filePath);
  changed.sort();
  return changed.slice(0, MAX_AUTOMATION_CHANGED_FILES);
```

**Flow:** runPi/runCustom snapshot `gitStatusSet(cwd)` BEFORE spawning → run executes (its tools create/edit/delete files) → computeChangedFiles re-runs porcelain and set-diffs both directions: additions (in-after-not-before) plus deletions (in-before-not-after).
**Invariant:** The diff is SYMMETRIC — deletions are changes too; a one-directional port misses files the run removed. Every failure mode (non-git cwd, git absent, timeout 5s, non-zero exit) resolves to an EMPTY set so the feature can never break a launch; renames surface under their NEW name only. Untracked-but-created files appear (porcelain includes them) without any tree-wide walk.
**Probe:** `packages/server/tests/agent-runner.test.ts` (`diffs git status before/after into changedFiles` :249–253 — fake pi creates agent-out.txt in an initialized repo; result.changedFiles contains it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", query: "gitStatusSet computeChangedFiles porcelain", limit: 10 });
```

## Verdict
Adopt the before/after symmetric set-diff over `git status --porcelain` as the zero-instrumentation impact report; adapt the cap. Directly tested through the real fake-pi integration path; failure-open behavior is source-pinned.
