<!-- capsule-v2 -->
# Progress sink — how do you render indexer internals into human progress without leaking noise to stdout?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** What visibility policy and line grammar turn worker JSON logs into a clean terminal progress UI?

## TTY/verbose gate + event-to-phrase renderer + TSan-safe carriage updates
**Path/Symbol:** `src/cli/cli.c:cbm_cli_progress_enabled` (tests 59–63) + `src/cli/progress_sink.{h,c}` + tests/test_cli.c:85–160.
**Signature:** `bool cbm_cli_progress_enabled(bool quiet_flag, bool verbose_flag);` / `void cbm_progress_sink_fn(const char *line);`
**Data Shape:** Enabled = quiet OR verbose (never both-false). Input lines are the structured log grammar (`level=info msg=pass.timing ...`, worker JSON like `{"event":"pipeline.discover","files":"3"}`); rendered output maps events to phrases (`Discovering files (3 found)`, `[1/9] Building file structure`) using carriage-return rewrites for in-place updates.

### Decisive source
```c
TEST(cli_progress_visibility_policy) {
    ASSERT_TRUE(cbm_cli_progress_enabled(true, false));
    ASSERT_TRUE(cbm_cli_progress_enabled(false, true));
    ASSERT_FALSE(cbm_cli_progress_enabled(false, false));
}
TEST(cli_progress_sink_accepts_worker_json_logs) {
    cbm_progress_sink_fn("{\"level\":\"info\",\"event\":\"pipeline.discover\",\"files\":\"3\"}");
    ...
    ASSERT_NOT_NULL(strstr(rendered, "Discovering files (3 found)"));
    ASSERT_NOT_NULL(strstr(rendered, "[1/9] Building file structure"));
```

**Flow:** CLI decides visibility once → sink initialized on stderr → worker log lines stream through the parser → recognized events update a single progress line (carriage rewrite), unrecognized pass silently → concurrent workers serialize through one mutex (the focused TSan guard).
**Invariant:** stdout stays reserved for machine-readable results; unknown events must never crash or spam — drop through.
**Probe:** `tests/test_cli.c:cli_progress_visibility_policy`, `cli_progress_sink_accepts_worker_json_logs`, `cli_progress_sink_serializes_concurrent_callbacks`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_progress_sink_fn", limit: 5 });
```

## Verdict
Adopt gated rendering over structured-log input for long-running CLIs; adapt the event→phrase table; omit carriage rewriting when your sink is a file.
