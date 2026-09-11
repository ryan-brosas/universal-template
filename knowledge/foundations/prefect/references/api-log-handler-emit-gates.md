<!-- capsule-v2 -->

# APILogHandler emit gates and deadlock-guarded flush — Which logs ship, which warn, and how do you flush from any context without deadlocking?

**Source:** prefect Apache-2.0 `main@ce79dd3d6cfa2b7337265498210dbc4d25bcdc98`; Codebase Memory `prefect`. **Question:** How does a logging.Handler decide to drop/opt-out/warn at emit time, truncate oversize payloads, and flush safely from sync, async, and interpreter-shutdown contexts?

## Three emit gates; missing-context ladder with caller-anchored warning; flush is triple-guarded

**Path/Symbol:** `src/prefect/logging/handlers.py:APILogHandler (113-289)` — `flush (121-145)`, `aflush (147-156)`, `emit (158-176)`, `handleError (178-199)`, `prepare (201-286)`.

**Signature:** `emit(self, record: logging.LogRecord)`; `prepare(self, record) -> Dict[str, Any]`; `flush()` / `@classmethod async aflush()`.

**Data Shape:** record extras `flow_run_id`, `task_run_id`, `worker_id`, `send_to_api` (default True); setting `PREFECT_LOGGING_TO_API_WHEN_MISSING_FLOW ∈ {warn, ignore, raise}`.

### Decisive source
```python
def emit(self, record):
    try:
        profile = get_settings_context()
        if not profile.settings.logging.to_api.enabled:
            return  # Respect the global settings toggle
        if not getattr(record, "send_to_api", True):
            return  # Do not send records that have opted out
        log = self.prepare(record)
        emit_api_log(log)
    except Exception:
        self.handleError(record)

def handleError(self, record):
    _, exc, _ = sys.exc_info()
    if isinstance(exc, MissingContextError):
        ... # warn (stacklevel=8 → user call site) | ignore | raise

# prepare(): flow_run_id = record attr → flow_run.id → task_run.flow_run_id;
# str→UUID coercion: except ValueError: flow_run_id = None  (log dropped)
# oversize: truncated_message = msg[:len - oversize - BUFFER(50)] + "... [truncated]"
```
```python
def flush(self):
    loop = get_running_loop()
    if loop:
        if in_global_loop():
            raise RuntimeError("Cannot call `APILogWorker.flush` from the global "
                "event loop; it would block ... Use `aflush` instead.")
        from_sync.call_soon_in_new_thread(create_call(APILogWorker.drain_all))
    else:
        APILogWorker.drain_all(timeout=5)  # logging._lock shutdown deadlock guard
```

**Flow:** every record passes three gates — global settings toggle, per-record opt-out extra, then `prepare()`, which resolves run linkage (explicit attrs win; else run-context flow/task fallback), coerces string UUIDs (invalid ⇒ None ⇒ dropped), formats the message, and truncates oversize payloads keeping a 50-char buffer so the re-serialized dict fits the cap. Failures route through stdlib `handleError`, where only MissingContextError gets the special warn/ignore/raise ladder — its warning uses stacklevel=8 so the reported line is the USER's logging call, not handler internals.

**Invariant:** (1) Flush must never block the global loop (RuntimeError there) and never block forever during logging-shutdown (`timeout=5` against the `logging._lock` vs worker-emit deadlock); from inside another loop it drains via a NEW thread because stdlib flush cannot await. (2) Truncation recomputes payload size AFTER truncation — the cap holds post-hoc, not pre-hoc.

**Probe:** direct tests `tests/test_logging.py:709 test_does_not_send_logs_that_opt_out`, `:720 test_does_not_send_logs_when_handler_is_disabled`, `:734 test_does_not_send_logs_outside_of_run_context_with_default_setting`, `:866 test_missing_context_warning_refers_to_caller_lineno` (warning lineno == caller's line), `:2456 test_prepare_truncates_oversized_log` (size ≤ max after truncation, suffix present).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "prefect", "name_pattern": "^APILogHandler$", "limit": 3}'
```
(observed rank-1: `APILogHandler Class src/prefect/logging/handlers.py 113-289`)

## Verdict
Adopt gate-laddered emit + caller-anchored missing-context warnings + triple-guarded flush for any logging→API bridge; adapt the settings surface; omit LogCreate schema details.
