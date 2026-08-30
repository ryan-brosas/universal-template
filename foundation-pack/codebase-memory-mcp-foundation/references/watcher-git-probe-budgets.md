<!-- capsule-v2 -->
# Watcher git probe budgets — how do you run `git status`-class commands inside a watcher without hangs or memory blowups?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What deadline/output caps make repository-controlled external config (fsmonitor hooks!) safe to invoke periodically?

## 30s wall-clock + 64 MiB capture + 4 KiB HEAD line cap
**Path/Symbol:** `src/watcher/watcher.c:131–134` + stop/cancel twins tests/test_watcher.c:924 (`watcher_stop_and_unwatch_cancel_blocked_git_without_backstop`).
**Signature:** constants: `WATCHER_GIT_DEADLINE_MS 30000`, `WATCHER_GIT_OUTPUT_MAX (64U*1024U*1024U)`, `WATCHER_GIT_HEAD_MAX 4096U`, poll slice `WATCHER_GIT_POLL_US 10000`.
**Data Shape:** Every git invocation carries a hard wall-clock deadline AND a finite capture budget; HEAD lines truncated at 4 KiB; polling loop slices 10ms so stop flags are honored mid-command.

### Decisive source
```c
/* Git is external and repository-controlled configuration may activate slow
 * helpers (for example fsmonitor). Every invocation therefore has both a hard
 * wall-clock deadline and a finite capture budget. */
```

**Flow:** watcher tick → spawn git with output capture → poll loop checks deadline/stop-flag every 10 ms → truncate per-line captures → classify change (HEAD movement vs dirty worktree) vs timeout → timeout treated as "no signal this round", never as crash.
**Invariant:** A repo can weaponize git hooks; treat every git subprocess as untrusted-for-latency and unbounded-for-output. Stop requests must preempt the wait, not queue behind it.
**Probe:** `tests/test_watcher.c:watcher_stop_and_unwatch_cancel_blocked_git_without_backstop`, `watcher_detects_git_commit`, `watcher_monorepo_subdir_ignores_sibling_changes`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "WATCHER_GIT_DEADLINE_MS", limit: 5 });
```

## Verdict
Adopt dual budget + preemptible polling for any periodic VCS subprocess; adapt caps to your cadence; the fsmonitor rationale is why wall-clock alone is insufficient.
