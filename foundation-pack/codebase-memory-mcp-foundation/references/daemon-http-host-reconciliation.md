<!-- capsule-v2 -->
# Daemon HTTP host reconciliation — how do you run a UI server inside a daemon that another process may also start?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What reconcile sequence lets daemon-owned and standalone UI servers coexist safely on one port?

## Prepare → drive → refuse-refusal lifecycle with forced terminate backstop
**Path/Symbol:** `src/daemon/host.c` + tests/test_daemon_runtime.c:1533–1692 (`cbm_daemon_host_state_prepare_for_test`, `http_reconcile_sequence_for_test`, `http_reconcile_free_refusal_for_test`, `host_force_terminate_for_test`).
**Signature:** test-driven sequence: prepare state → reconcile sequence → free-refusal path; watchdog via `cbm_daemon_host_force_terminate_for_test("noncooperative_callback")`.
**Data Shape:** The daemon host owns the HTTP thread lifecycle; reconciliation detects an already-listening server, adopts or defers, and refuses destructive frees while callbacks are in flight; a watchdog force-terminates non-cooperative shutdown paths.

### Decisive source
```c
bool driven = cbm_daemon_host_http_reconcile_sequence_for_test(...);
bool refused = cbm_daemon_host_http_reconcile_free_refusal_for_test(&result);
cbm_daemon_host_force_terminate_for_test("noncooperative_callback");
```

**Flow:** daemon start prepares host state bound to the endpoint → reconcile probes the UI port: if owned by us, adopt; if foreign, defer/standby → stop path refuses to free while request threads are live (refusal is a RESULT, not a hang) → watchdog escalates to force-terminate for non-cooperative callbacks so `daemon stop` always terminates.
**Invariant:** Free-refusal must be observable and bounded — silent blocking inside a callback is exactly what the watchdog exists to kill.
**Probe:** the four named tests above; end-to-end liveness via tests/test_httpd.c:`ui_server_stop_joins_cleanly`, `ui_server_stop_interrupts_partial_request_within_one_second`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "host_reconcile", limit: 5 });
```

## Verdict
Adopt reconciled adoption + refusal-as-result + watchdog escalation for embedded servers in shared daemons; adapt ownership probing to your socket layer; omit TSan variants outside sanitizer legs.
