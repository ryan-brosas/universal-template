<!-- capsule-v2 -->
# Daemon bootstrap launch spec — how do you spawn a detached daemon whose stdio can NEVER corrupt yours?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What fields must a launch spec set so a background MCP daemon starts cleanly?

## Detached, non-inheriting, no-shell internal-argv spawn
**Path/Symbol:** `src/daemon/bootstrap.c:cbm_daemon_bootstrap_launch_spec_init` (250–264).
**Signature:** `bool cbm_daemon_bootstrap_launch_spec_init(const char *executable_path, cbm_daemon_bootstrap_launch_spec_t *spec_out);`
**Data Shape:** Sets: argv[0]=executable_path, argv[1]=`CBM_DAEMON_INTERNAL_ARG` (the worker/internal grammar marker), argc=2, detached=true, inherit_standard_handles=false, use_shell=false.

### Decisive source
```c
spec_out->argv[1] = CBM_DAEMON_INTERNAL_ARG;
spec_out->detached = true;
spec_out->inherit_standard_handles = false;
spec_out->use_shell = false;
```

**Flow:** caller resolves executable path → init spec → platform layer spawns detached with fresh pipes → child classifies itself as the internal role via argv[1] and never inherits the parent's stdin/stdout — critical because an MCP parent's stdio IS the client wire.
**Invariant:** Internal-role dispatch by argv marker (not env); stdio inheritance must be OFF or the daemon will speak JSON-RPC into your terminal.
**Probe:** `tests/test_daemon_bootstrap.c` suite covers role classification around this contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_bootstrap_launch_spec_init", limit: 5 });
```

## Verdict
Adopt explicit-spec detachment for self-daemonizing tools; adapt the marker arg; test the classification matrix, not just the happy path.
