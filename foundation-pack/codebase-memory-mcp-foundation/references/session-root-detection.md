<!-- capsule-v2 -->
# Session-root detection — how does a serverless-feeling MCP tool figure out WHICH repo you mean?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How is the working repo derived from CWD once per session, and why must it reuse the pipeline's naming function?

## One-shot CWD detection with useless-root skips
**Path/Symbol:** `src/mcp/mcp.c:detect_session` (11492–11519) + auto_watch gate (11521–11535).
**Signature:** `static void detect_session(cbm_mcp_server_t *srv);`
**Data Shape:** Skips `/` and `$HOME` as useless roots; derives project name via `cbm_project_name_from_path(session_root)`; latched by `session_detected` so later calls are no-ops even if CWD changed.

### Decisive source
```c
/* 1. Try CWD */
if (getcwd(cwd, sizeof(cwd)) != NULL) {
    /* Skip useless roots: / and $HOME */
    if (strcmp(cwd, "/") != 0 && (home == NULL || strcmp(cwd, home) != 0)) { ... }
}
/* Derive project name from path — must match cbm_project_name_from_path
 * used by the pipeline, otherwise session queries look for a .db file
 * that doesn't match the indexed project name. */
```

**Flow:** first initialize → detect_session latches root+project → auto-index/watcher decisions consume them (see auto-index gating capsule) → subsequent tool calls without explicit `project` target the session project.
**Invariant:** Naming-function reuse is the contract; a second derivation algorithm guarantees eventual DB-name drift. Latch prevents mid-session root flapping.
**Probe:** tests/test_mcp.c around 10451/10606 exercise the same derivation on cwd within server tests (`mcp_auto_watch_false_skips_supervised_autoindex_issue853` depends on it).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "detect_session", limit: 5 });
```

## Verdict
Adopt latched single-shot context detection with shared naming; adapt skip-list roots; omit watcher registration if your deployment re-indexes externally.
