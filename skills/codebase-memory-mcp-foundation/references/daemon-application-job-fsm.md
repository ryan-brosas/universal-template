<!-- capsule-v2 -->
# Daemon application job FSM — how do you run index jobs under a daemon with cancellation that never orphans work?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What lifecycle rules govern subscribed jobs, physical cancel timing, and late watcher sessions?

## Terminal-subscription isolation + cancel-after-final-session + admission staleness checks
**Path/Symbol:** `src/daemon/application.c` + tests/test_daemon_application.c:2695 (`fresh_request_does_not_reuse_terminal_subscribed_job`), 2944 (`cancels_physical_job_only_after_final_session`), 3416/3463/3516/3624 (watcher callback admission, final-cancel drain, live-watch ownership, late-session ownership).
**Signature:** runtime application callbacks (`cbm_daemon_runtime_application_callbacks`) exposing open/poll/cancel per session; worker ops injected for tests.
**Data Shape:** Jobs keyed with session sets; terminal jobs are NOT reusable by fresh requests (fresh id ⇒ fresh job); physical process cancellation happens ONLY after the last subscribing session closes; watcher-driven jobs validate exact live-watch ownership at admission.

### Decisive source
```c
TEST(daemon_application_fresh_request_does_not_reuse_terminal_subscribed_job) { ... }
TEST(daemon_application_cancels_physical_job_only_after_final_session) { ... }
TEST(daemon_application_stale_watcher_callback_is_rejected_at_job_admission) { ... }
TEST(daemon_application_late_watcher_session_owns_active_watcher_job) { ... }
```

**Flow:** session opens → tool call admits a job (stale watcher callbacks rejected here) → multiple sessions may subscribe → poll streams progress → cancel requests mark intent; physical kill deferred to final session close → completion publishes via the normal staging pipeline → late sessions attaching must take ownership of the ACTIVE job, not fork state.
**Invariant:** Job identity and subscription are separate concerns — conflating them causes both premature kills and zombie work.
**Probe:** the four named tests plus `daemon_application_serializes_adr_mutation_with_index_job` (ADR vs index serialization).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "application", limit: 5 });
```

## Verdict
Adopt subscribe/own/terminal job semantics for daemonized long tasks; adapt the ops-injection seams; watcher-callback staleness rejection is the transferable gem.
