<!-- capsule-v2 -->
# Subprocess outcome classification — what does a supervisor need to know about HOW a child died?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Beyond exit codes, which six-way classification and quiet-timeout semantics make crash/hang containment actionable?

## Six-outcome classifier + quiet-timeout hang detection
**Path/Symbol:** `src/foundation/subprocess.h` (contract 1–60) + `cbm_proc_classify` (146–150) + tests/test_subprocess.c:29–43.
**Signature:** `cbm_proc_outcome_t cbm_proc_classify(bool exited_normally, int exit_code, int term_signal, ...);`
**Data Shape:** Outcomes: CLEAN (exit 0), EXIT_NONZERO, CRASH (POSIX SIGSEGV/BUS/ILL/FPE/ABRT/SYS or Windows NTSTATUS ≥0xC0000000: 0xC0000005 AV, 0xC00000FD stack overflow…), HANG (no new log line within quiet window ⇒ killed), KILLED (foreign non-fault signal), SPAWN_FAILED. Result adds cancellation_requested / forced / tree_quiesced / supervision_failed flags.

### Decisive source
```c
/* 2. A quiet-timeout — kill + report HANG when the child makes no progress
 *    (emits no new log line) for a configurable window. This catches external
 *    tree-sitter scanners that infinite-loop (a hang, not a crash).
 * The reap loop is EINTR-safe. Line tailing keeps a partial final line buffered
 * while the child tree can still write, then delivers that final fragment once
 * the tree is quiescent. */
```

**Flow:** spawn with line-tailed stdout/stderr → each delivered chunk resets the quiet timer → wait loop (EINTR-safe) → on exit classify via WIFSIGNALED/WTERMSIG or NTSTATUS bands → quiet expiry ⇒ kill process group and report HANG → partial last line delivered only after the tree quiesces.
**Invariant:** HANG is a progress notion, not wall-clock — chatty children never false-positive; classification must distinguish "we killed it after silence" from foreign kills.
**Probe:** `tests/test_subprocess.c:subprocess_classify_clean`, `subprocess_classify_exit_nonzero`, `subprocess_classify_windows_crash_codes`; consumer contract in `tests/test_index_supervisor.c:index_supervisor_sync_wrapper_forwards_cancel_and_drains_tree`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_proc_classify", limit: 5 });
```

## Verdict
Adopt the six-way taxonomy + progress-based hang detection for any supervisor; adapt signal/NTSTATUS lists to platform; omit tree-quiesce accounting if you don't kill groups.
