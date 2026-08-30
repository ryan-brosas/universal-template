<!-- capsule-v2 -->
# Watcher baseline discipline — when does re-watching a project reset its dirty baseline, and why does it matter?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you prevent a watch re-registration from either losing pending changes or firing spurious reindexes?

## Identical-watch preserves the dirty baseline
**Path/Symbol:** `tests/test_watcher.c:watcher_identical_watch_preserves_dirty_baseline` (1442–1487).
**Signature:** `cbm_watcher_watch(w, project, root_path)` semantics on repeat registration.
**Data Shape:** A watch entry carries per-project change baselines (HEAD + dirty snapshot). Re-registering an IDENTICAL (project, root) must keep existing baselines; only a genuine root change replaces state. Positive index-callback return commits new baselines; skipped/failed keeps changes pending.

### Decisive source
```c
TEST(watcher_identical_watch_preserves_dirty_baseline) { ... }
/* Only a 0 return commits the watcher's change baselines — a skipped or failed
 * reindex keeps the change pending so it is retried, never silently lost (#937). */
```

**Flow:** detect change → invoke index callback → 0 ⇒ capture new HEAD/dirty baseline; positive ⇒ leave pending for next poll; negative ⇒ error path retains pending state too → duplicate watch calls no-op with baselines intact → monorepo subdirs scope their own baselines so sibling edits don't fire (`watcher_monorepo_subdir_ignores_sibling_changes`).
**Invariant:** Baseline commit is transactional with successful indexing — decoupling them creates infinite-reindex or silent-loss loops.
**Probe:** `tests/test_watcher.c:watcher_identical_watch_preserves_dirty_baseline`, `watcher_detects_sha256_git_commit`, `watcher_nested_non_git_dir_does_not_inherit_ancestor_dirt`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "watch", limit: 5 });
```

## Verdict
Adopt success-committed baselines and idempotent identical-watch registration for any polling indexer; adapt change signals; nested-dir dirt inheritance rules are easy to get wrong — test them.
