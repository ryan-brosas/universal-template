<!-- capsule-v2 -->
# Exit-time flush choreography — how are open spans flushed at interpreter exit even when atexit is skipped?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** Which hooks run in which order at process exit, and why is os._exit patched?

## exit_open_spans / shutdown_otlp_forwarding / patched_os_exit
**Path/Symbol:** `logfire/_internal/config.py:exit_open_spans` (`config.py:1859-1906`).
**Signature:** module-level `os._exit = patched_os_exit` executed AT IMPORT; `atexit.register(exit_open_spans)` re-registered on every `_initialize`.
**Data Shape:** `_LOGFIRE_CONFIG_INSTANCES: list[weakref.ref[LogfireConfig]]` tracks every configured instance.

### Decisive source
```python
def exit_open_spans():  # pragma: no cover
    for span in list(OPEN_SPANS.values()):
        span.end()
        # Interpreter shutdown may trigger another call to .end(),
        # which would log a warning "Calling end() on an ended span."
        span.end = lambda *_, **__: None      # neuter AFTER first end

# OTEL registers its own atexit callback in the tracer/meter providers to shut them down.
# Registering this callback here after the OTEL one means that this runs first.
# Otherwise OTEL would log an error "Already shutdown, dropping span."
atexit.unregister(exit_open_spans)
atexit.register(exit_open_spans)
...
# atexit isn't called in forked processes, patch os._exit to ensure cleanup.
original_os_exit = os._exit
def patched_os_exit(code):
    try:
        exit_open_spans()
        for config_ref in _LOGFIRE_CONFIG_INSTANCES:
            config = config_ref()
            if config is not None: config.force_flush()
        cleanup_disk_retryers()
    except: pass                               # noqa — weird errors during shutdown, ignore ALL
    return original_os_exit(code)
os._exit = patched_os_exit
```
OPEN_SPANS itself is a WeakValueDictionary keyed `(trace_id, span_id)` (`tracer.py:51`) holding suspended-generator spans that GC would end "too late"; `Logfire.shutdown` order: variable_provider → otlp_forwarding(drain) → tracer force_flush+shutdown → logger flush+shutdown → meter flush+shutdown, each with `remaining_ms()` budget arithmetic returning whether time remained.
**Flow:** normal exit: logfire's atexit callback fires BEFORE OTEL's (registration-order guarantee, re-un/registered per initialize to stay ordered after re-configures) ending open spans then letting providers flush; forked child calling os._exit: the patch replays the same cleanup synchronously; disk retryers get their temp dirs rmtree'd either via atexit weakref sweep or the patch.
**Invariant:** The lambda-neutering of `span.end` prevents double-end warnings when GC later collects the generator frame. Ordering vs OTEL's callbacks is load-bearing, hence unregister-before-register. Bare except in the patch is deliberate ("weird errors can happen during shutdown").
**Probe:** `tests/test_configure.py::test_atexit` family — pins end-once semantics and hook ordering.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "exit_open_spans OPEN_SPANS patched_os_exit shutdown_otlp_forwarding", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: weakref instance registry, atexit-ordering control, open-span registry with end-neutering, os._exit patch for fork-heavy hosts. Adapt budgets to your exporter latencies. Omit forwarding-manager drain if unported.
