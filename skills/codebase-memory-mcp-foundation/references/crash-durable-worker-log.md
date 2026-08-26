<!-- capsule-v2 -->
# Crash-durable worker log — how do you guarantee a post-mortem log says SOMETHING even if the process dies mid-line?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** How do you convert "worker died, 0-byte log" into an attributable report?

## Unbuffered stderr + per-line flush + synchronous startup header
**Path/Symbol:** `src/foundation/log.c:cbm_log_set_crash_durable` (39–48) + `emit_line` (235–254); worker-side `src/mcp/index_supervisor.c:cbm_index_worker_log_begin`.
**Signature:** `void cbm_log_set_crash_durable(bool enabled);`
**Data Shape:** Enabled ⇒ setvbuf(stderr, NULL, _IONBF, 0) best-effort PLUS a per-line `fflush(stderr)` after every emitted line; the worker writes a startup header (version, build fingerprint, pid, repo path, argv) synchronously before any work; idempotent because the role is installed twice.

### Decisive source
```c
/* Best effort by contract: setvbuf is only guaranteed before a stream's
 * first operation, so a process that has already written to stderr keeps its
 * buffering. The per-line flush in emit_line is what makes the durability
 * guarantee hold either way. */
...
/* Six reports (#1070,#1130,#1132,#1133,#1145,#1450) describe a worker that died
 * and left a log of 0 bytes ... It fixes no crash. It converts an empty file
 * into a report we can act on. */
```

**Flow:** worker role detected at process entry (BEFORE anything else writes) → setvbuf unbuffered → header written and flushed → every subsequent line flushed individually → a crash/SIGKILL/hang leaves everything already emitted on disk.
**Invariant:** setvbuf only binds pre-first-write — ordering IS the feature; per-line flush is what makes durability hold even when setvbuf was refused.
**Probe:** `tests/test_index_supervisor.c:index_supervisor_killed_worker_log_is_never_empty_and_names_the_run` and `index_supervisor_terminal_log_lifecycle_matches_outcome_and_profiling`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_log_set_crash_durable", limit: 5 });
```

## Verdict
Adopt unbuffered+flush-per-line for any supervised-child log; adapt the header fields to your diagnostics; omit the sink-tee machinery unless you mirror logs to files.
