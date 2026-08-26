<!-- capsule-v2 -->
# Daemon job serialization — how do you make ADR edits and index jobs cooperate instead of corrupting each other?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What admission/serialization contract keeps concurrent daemon jobs per project safe, including watcher callbacks?

## Job admission with mutation guard + watcher callback rejection
**Path/Symbol:** `tests/test_daemon_application.c` — `daemon_application_serializes_adr_mutation_with_index_job` (3722+), `daemon_application_stale_watcher_callback_is_rejected_at_job_admission` (3416+), worker-lock twin (4115+); engine src/daemon/application.c.
**Signature:** runtime application callbacks: `cbm_daemon_runtime_application_callbacks(application)` → open session → submit tool call (index_repository / manage_adr).
**Data Shape:** Jobs carry a project scope; ADR mutation and indexing serialize through the project worker lock; stale watcher reindex callbacks are rejected AT ADMISSION when their watch generation is superseded.

### Decisive source
```c
TEST(daemon_application_serializes_adr_mutation_with_index_job) {
    ... app_fake_worker_context_init(&fake);  /* injectable worker ops */
    cbm_daemon_runtime_application_session_t *index_session = ...;
    cbm_daemon_runtime_application_session_t *adr_session   = ...;
    snprintf(adr_args, ..., "{\"project\":\"%s\",\"mode\":\"update\",\"content\":\"serialized ADR\"}", ...);
```
```c
TEST(daemon_application_stale_watcher_callback_is_rejected_at_job_admission) { ... }
```

**Flow:** sessions open per client → tool submissions become jobs admitted under the per-project mutation guard (see project-lock capsule) → an in-flight index job blocks ADR writes until terminal (and vice versa) → watcher-originated reindexes validate their watch identity at admission so a superseded callback can't resurrect stale state → cancel drains only after final sessions close.
**Invariant:** Serialization is by PROJECT scope, not global; admission-time validation must reject stale async callbacks rather than racing them mid-flight.
**Probe:** the two named tests above plus `daemon_application_final_cancel_drains_admitted_watcher_job`, `daemon_application_cancels_physical_job_only_after_final_session`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_daemon_runtime_application_callbacks", limit: 5 });
```

## Verdict
Adopt scoped-job serialization + admission-time staleness checks for any multi-client daemon; adapt the ops-injection seam to your test stack; omit the HTTP reconcile machinery if you have no embedded UI host.
