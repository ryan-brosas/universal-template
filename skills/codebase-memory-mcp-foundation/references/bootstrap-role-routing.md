<!-- capsule-v2 -->
# Daemon bootstrap role routing — how does ONE binary decide between MCP server, daemon, CLI, hook, and worker?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How is argv classified into process roles, and why does `cli search "daemon start"` stay LOCAL_CLI?

## Ordered role classification with quoted-input precedence
**Path/Symbol:** `src/daemon/bootstrap.c:cbm_daemon_process_role` (~150–205) + `bootstrap_runtime_parent_override` (227–230).
**Signature:** `cbm_daemon_process_role_t cbm_daemon_process_role(int argc, char **argv);`
**Data Shape:** Roles: STATELESS (version/help + stateless command list), DAEMON_CTL (`daemon` subcommand unless followed by --help), MCP_CLIENT (default), LOCAL_CLI (explicit `cli` verb — checked BEFORE the daemon match so tool input containing "daemon" never routes to daemon control), HOOK_CLIENT, WORKER (internal arg), INVALID.

### Decisive source
```c
/* Placed after the `cli` check on purpose: `cbm cli search "daemon start"`
 * is opaque tool input and must stay LOCAL_CLI. */
if (bootstrap_arg_is(argv[arg], "daemon")) {
    return ... CBM_DAEMON_PROCESS_DAEMON_CTL;
}
```
```c
/* cbm_safe_getenv never truncates: a value too long for the buffer is reported
 * as absent, so no half a path can ever become a runtime parent. */
```

**Flow:** main → classify role → WORKER installs crash-durable logging before anything else writes; INVALID exits with usage → MCP/daemon roles proceed to endpoint+cohort admission; env overrides for runtime parent are length-checked via safe-getenv so truncated paths can't become rendezvous parents.
**Invariant:** Verb matching must respect quoting boundaries (opaque strings after `cli` are data); classification happens before ANY side effect.
**Probe:** `tests/test_daemon_bootstrap.c` suite; end-to-end role behavior in tests/test_cli.c activation flows.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_process_role", limit: 5 });
```

## Verdict
Adopt single-classifier role routing with explicit precedence comments; adapt your verb list; the safe-getenv no-truncation rule generalizes to every env-sourced path.
