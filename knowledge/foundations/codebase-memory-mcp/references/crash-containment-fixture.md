<!-- capsule-v2 -->
# Crash containment fixture — how do you test "one poisoned file must not kill the index"?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What's the fork-isolated pattern for proving crash quarantine works?

## Poison file + good files + fork + signal inspection
**Path/Symbol:** `src/mcp/index_supervisor.c` (worker respawn) + tests/test_mcp.c:10345 (`index_recovery_parallel_quarantines_crasher`), 10289 (`index_second_inprocess_run_survives_issue773`), 9581 (`unsafe_clean_is_never_fallback_or_recovery`).
**Signature:** POSIX-only (SKIP_PLATFORM on Windows — fork isolation required); supervisor respawns worker after SIGSEGV-class death.
**Data Shape:** Fixture: two good .py files + idxpar_crasher.py engineered to crash the parser; child process exit inspected via waitpid status/signal; expectation: crash contained to the poison file, good files indexed, DB never left half-published.

### Decisive source
```c
snprintf(pc, sizeof(pc), "%s/idxpar_crasher.py", tmp_dir);
fputs("def idxpar_crash_fn():\n    return 'boom'\n", f);
int code = -1; bool signalled = false; int sig = 0;
```

**Flow:** build repo with poison → run indexing under supervision (forked) → inspect child termination signal → assert quarantine of offender + survival of siblings.
**Invariant:** Crash tests MUST be process-isolated (ASan won't catch SIGBUS in-process); "recovery" paths must never silently become "clean" paths (9581 pins that too).
**Probe:** `tests/test_mcp.c:index_recovery_parallel_quarantines_crasher`, `index_second_inprocess_run_survives_issue773`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "quarantines_crasher", limit: 5 });
```

## Verdict
Adopt poison-file fixtures with real process isolation for fault-tolerance claims; adapt crash triggers; assert BOTH containment and sibling survival.
