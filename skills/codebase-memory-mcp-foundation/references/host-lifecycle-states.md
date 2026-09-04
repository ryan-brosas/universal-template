<!-- capsule-v2 -->
# Daemon host lifecycle — how does the daemon own (and surrender) an HTTP server another process might want?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What are the prepare/reconcile/refuse/terminate states for daemon-owned HTTP, and how do tests drive them?

## State machine with test-injected decisions and labeled watchdog
**Path/Symbol:** `src/daemon/host.c` + `host_internal.h` + tests/test_daemon_runtime.c:1533–1692.
**Signature:** `cbm_daemon_host_state_prepare_for_test(endpoint)` → reconcile sequence → free-refusal probe → `force_terminate_for_test("noncooperative_callback")`.
**Data Shape:** States: prepared → reconciled (adopted/deferred/listening) → stopping (free-refusal while callbacks live) → terminated. Refusal carries a reason; termination labels its victim.

### Decisive source
```c
bool driven = cbm_daemon_host_http_reconcile_sequence_for_test(
    /* adopt / defer / listen transitions */);
bool refused = cbm_daemon_host_http_reconcile_free_refusal_for_test(&result);
cbm_daemon_host_force_terminate_for_test("noncooperative_callback");
```

**Flow:** daemon start prepares host bound to endpoint → reconcile decides ownership vs the standalone server → shutdown requests free only when no callback is in flight (refusal is returned, not hung) → watchdog force-terminates named non-cooperative paths so `daemon stop` always completes.
**Invariant:** Every blocking wait has an interrupt path; every forced kill names its target for post-mortems.
**Probe:** tests/test_daemon_runtime.c:1533/1555/1576/1599/1692.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "host", limit: 5 });
```

## Verdict
Adopt explicit state machines for embedded-server ownership; adapt transitions; refusal-as-value beats exception-or-hang in C-style hosts.
