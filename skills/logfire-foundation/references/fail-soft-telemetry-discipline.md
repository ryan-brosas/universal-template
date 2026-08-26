<!-- capsule-v2 -->
# Fail-soft telemetry discipline — how does an observability SDK guarantee it never crashes the app it observes?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What is the complete error-containment toolkit, and where must each layer be applied so user code always survives internal failures?

## handle_internal_errors / NoopSpan / suppress_instrumentation / log_internal_error
**Path/Symbol:** `logfire/_internal/utils.py:HandleInternalErrors + log_internal_error` (`utils.py:314-411`) + `main.py:NoopSpan` (`main.py:3287-3343`) + `_span` catch-all (`main.py:278-280`).
**Signature:** `handle_internal_errors: HandleInternalErrors` (usable as CM and decorator); `log_internal_error()` re-raises under pytest unless the test opts out (`PYTEST_CURRENT_TEST` and not 'test_internal_exception').
**Data Shape:** internal-error logging routes through stdlib `logging.getLogger('logfire')`, wrapped in `suppress_instrumentation()` "to prevent infinite recursion from the logging integration".

### Decisive source
```python
# main.py _span tail:
except Exception:
    log_internal_error()
    return NoopSpan()      # with logfire.span(...): span.set_attribute(...) keeps working

# utils.py log_internal_error:
with suppress_instrumentation():
    try:
        logger.exception('Caught an internal error in Logfire. '
            'Your code should still be running fine, just with less telemetry. ...')
    except Exception: pass
```
NoopSpan contract: `__getattr__` returns a no-op lambda for ANY method; explicit properties (message_template='' , tags=(), message='') exist ONLY so setters/properties don't blow up — including `span._span` returning `trace_api.INVALID_SPAN` and `is_recording() -> False`. `LogfireSpan`/`FastLogfireSpan`/`NoopSpan` carry a cross-reference comment ("Changes to this class may need to be reflected in …"). Decorator usage wraps every processor on_start/on_end in the pipeline wrappers. The traceback-tweaking helper (`_internal_error_exc_info`) rebuilds the traceback skipping handler frames and keeping ≤3 user frames.
**Flow:** exception inside span creation/formatting/processors → contained at the nearest handle_internal_errors or try/except → logged once through the suppressed logger → execution continues with a NoopSpan or skipped phase → user's `with` block and attribute calls behave as if telemetry were disabled.
**Invariant:** Suppression MUST wrap the error report itself (else the report creates spans which fail which report…). pytest re-raise behavior makes silent internal breakage visible in the project's own test suite while production stays quiet. NoopSpan must implement every surface users touch — that's why it duplicates property/setter shapes explicitly.
**Probe:** `tests/test_internal_exceptions.py` — pins containment for each entrypoint.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "handle_internal_errors NoopSpan log_internal_error suppress_instrumentation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-layer discipline (CM/decorator containment, noop stand-ins, self-suppressed reporting, test-mode re-raise) for any instrumentation library. Adapt logger plumbing to host. Omit traceback surgery if your logger already attributes frames.
