<!-- capsule-v2 -->
# Daemon auto-index gating — when a client connects in an unindexed repo, who decides to build the graph?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What gates prevent surprise indexing of huge or private repos on session start?

## Session detect → already-indexed short-circuit → config + file-count budget
**Path/Symbol:** `src/mcp/mcp.c:detect_session` (11492–11519), `maybe_auto_index` (11622–11672), `register_watcher_if_enabled` (11533+).
**Signature:** `static void maybe_auto_index(cbm_mcp_server_t *srv);`
**Data Shape:** Gates in order: (1) session_root detected from CWD (skipping `/` and `$HOME`); (2) `<cache>/<project>.db` exists ⇒ skip indexing, only register watcher; (3) `auto_index` config bool (default FALSE, with actionable hint log); (4) tracked-file count ≤ `auto_index_limit` (default CBM_MCP_DEFAULT_AUTO_INDEX_LIMIT) via git ls-files — OOM guard.

### Decisive source
```c
/* Check if project already has a DB */
if (cbm_file_size(db_check) >= 0) {
    /* Already indexed → register watcher for change detection */
    cbm_log_info("autoindex.skip", "reason", "already_indexed", ...);
    register_watcher_if_enabled(srv); return;
}
...
if (!cbm_mcp_auto_index_within_file_limit(srv->session_root, file_limit, &file_count)) {
    cbm_log_warn("autoindex.skip", "reason", file_count >= 0 ? "too_many_files" : ..., ...);
    return;
}
```

**Flow:** initialize → detect_session derives root+project (MUST use the same name function as the pipeline) → if DB missing AND auto_index enabled AND repo small ⇒ spawn detached autoindex thread (supervisor-contained); else log why not and, when indexed, attach the adaptive watcher.
**Invariant:** Project-name derivation symmetry is load-bearing; auto_index defaults OFF so first contact never mutates state without consent.
**Probe:** `tests/test_mcp.c:mcp_auto_watch_false_skips_supervised_autoindex_issue853` plus index-supervisor containment (`tests/test_mcp.c:index_recovery_parallel_quarantines_crasher`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "maybe_auto_index", limit: 5 });
```

## Verdict
Adopt the four-gate ladder for any implicit background work on connect; adapt limits/config keys; omit the UI-open handshake if you have no embedded browser.
