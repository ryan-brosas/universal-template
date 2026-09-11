<!-- capsule-v2 -->
# Index supervisor — how do you keep one pathological file from killing your whole server process?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How should a parent supervise crash-prone work in a child, and what must the worker argv carry?

## fork+exec re-invocation with build-bound grammar
**Path/Symbol:** `src/mcp/index_supervisor.c` (module) + `src/mcp/index_supervisor.h:cbm_index_worker_invocation_t` (header 60–110).
**Signature:** `void cbm_index_set_worker_role(bool is_worker, const char *response_out);` / `bool cbm_index_supervisor_capture_build_fingerprint(void);`
**Data Shape:** Child = SAME binary re-invoked with hidden `--index-worker*` args: `--index-worker-single-thread`, `--index-worker-marker`, `--index-worker-quarantine`, `--index-worker-memory-budget-bytes`, `--index-worker-build` (64-hex executable fingerprint). Result string is written to `response_out` file for the parent to read back.

### Decisive source
```c
/* fork+exec only (never fork-and-run-in-child): the server holds persistent
 * threads plus mimalloc/sqlite global state with no pthread_atfork, so a
 * fork without exec would be a latent deadlock. Recursion is prevented by an
 * argv flag (`--index-worker`), never an ambient env var. */
```
```c
/* Capture the exact executable-image fingerprint once, during process startup
 * before any worker can be launched. Repeated calls return the original capture
 * and never re-hash a pathname that an installer may since have replaced. */
```

**Flow:** parent captures build fingerprint at startup → spawn self with build-bound argv grammar → child installs worker role (idempotent), writes a crash-durable startup header to its log BEFORE any work, runs indexing in-process WITHOUT re-supervising → parent reaps, classifies outcome via `cbm_proc_classify` {clean, exit-nonzero, crash, hang, killed, spawn-failed}, reads response file; oversized responses are contained and logs retained.
**Invariant:** The gate MUST NOT re-supervise inside a worker (argv flag, not env); a dead worker's log must never be empty (crash-durable stderr + synchronous header) — six unattributable crash reports motivated this.
**Probe:** `tests/test_index_supervisor.c:index_supervisor_worker_argv_requires_exact_build_bound_grammar`, `index_supervisor_killed_worker_log_is_never_empty_and_names_the_run`, `index_supervisor_oversized_response_is_contained_and_log_is_retained`; classification in `tests/test_subprocess.c:subprocess_classify_windows_crash_codes`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_index_supervisor_capture_build_fingerprint", limit: 5 });
```

## Verdict
Adopt fork+exec-only supervision, the argv-flag recursion guard, and the never-empty worker log; adapt the outcome taxonomy to your signals/NTSTATUS set; omit the memory-budget arg plumbing if your workers are single-threaded by construction.
