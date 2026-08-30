<!-- capsule-v2 -->
# Watcher adaptive polling — how do you watch many repos for git changes without inotify storms, and when is deletion safe?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How should a poll-based watcher scale intervals with repo size and gate destructive pruning?

## 5s base + 1s/500 files (cap 60s) + streak+grace prune
**Path/Symbol:** `src/watcher/watcher.c:cbm_watcher_poll_interval_ms` (146–152) + prune constants (117–126).
**Signature:** `int cbm_watcher_poll_interval_ms(int file_count);`
**Data Shape:** Interval = `5000 + (files/500)*1000` ms clamped to 60000. Prune requires BOTH `MISSING_ROOT_DELETE_AFTER = 3` consecutive missing polls AND a sustained-absence grace window (`PRUNE_GRACE_DEFAULT_S 600`, env-overridable) measured from the FIRST miss. Git probes carry a 30s deadline and 64 MiB output cap.

### Decisive source
```c
/* Stale-root pruning (#286): a watched project whose root directory stays
 * missing is pruned — its cached DB is deleted ... Deletion is destructive
 * (the DB can hold user-authored data such as the ADR), so it requires BOTH a
 * streak of consecutive missing polls AND a sustained-absence grace window ... */
#define MISSING_ROOT_DELETE_AFTER 3
#define PRUNE_GRACE_DEFAULT_S 600
```

**Flow:** per-project poll loop → probe HEAD movement or dirty worktree via bounded git invocations → on change call index callback; ONLY a 0 return commits new baselines (positive = skipped/retry next poll so changes are never silently lost; #937) → recompute adaptive interval → root-missing classification feeds streak/grace-gated prune with daemon mutation-guard begin/end around DB deletion.
**Invariant:** Baselines commit only on success — a skipped reindex keeps the change pending; destructive prune needs two independent signals plus guard balance.
**Probe:** `tests/test_watcher.c:poll_interval_base/scaling/cap`, `watcher_prunes_sustained_missing_root`, `watcher_grace_window_blocks_prune`, `watcher_identical_watch_preserves_dirty_baseline`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_watcher_poll_interval_ms", limit: 5 });
```

## Verdict
Adopt size-adaptive polling and the dual-signal prune gate for any watch system over mutable caches; adapt the interval constants to your fleet; omit the daemon guard trio if prunes are centralized.
