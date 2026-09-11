<!-- capsule-v2 -->
# Daemon host HTTP reconcile — how do you test "who owns the UI port" without real sockets flaking?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What seam shape lets reconcile logic be driven deterministically in tests?

## State-prepare + sequence-for-test + free-refusal-for-test seams
**Path/Symbol:** `tests/test_daemon_runtime.c:1533–1699` (`cbm_daemon_host_state_prepare_for_test(endpoint)`, `cbm_daemon_host_http_reconcile_sequence_for_test(...)`, `cbm_daemon_host_http_reconcile_free_refusal_for_test(&result)`, `cbm_daemon_host_force_terminate_for_test`).
**Signature:** three injected drivers returning bool/struct results; watchdog path exercised via force_terminate with a named noncooperative callback.
**Data Shape:** Reconcile result carries ownership decision + refusal reason; free-refusal returns a structured result rather than blocking; force-terminate takes a LABEL for the diagnostic trail.

### Decisive source
```c
bool prepared = endpoint && cbm_daemon_host_state_prepare_for_test(endpoint);
bool driven = cbm_daemon_host_http_reconcile_sequence_for_test(...);
bool refusal = cbm_daemon_host_http_reconcile_free_refusal_for_test(&result);
cbm_daemon_host_force_terminate_for_test("noncooperative_callback");
```

**Flow:** prepare host state from a validated endpoint → drive the reconcile sequence (adopt/defer/listen decisions) → assert free-refusal when callbacks are live → watchdog escalates with the callback's name recorded.
**Invariant:** Test seams must inject DECISIONS, not fake sockets — the logic under test is ownership/refusal ordering, which is exactly where socket-level tests flake.
**Probe:** tests/test_daemon_runtime.c:1533, 1555, 1576, 1599, 1692.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "http_reconcile", limit: 5 });
```

## Verdict
Adopt decision-injection seams for concurrency lifecycle testing; adapt to your host; label-carrying force-terminate is worth copying for post-mortems.
