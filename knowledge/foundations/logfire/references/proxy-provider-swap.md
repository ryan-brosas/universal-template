<!-- capsule-v2 -->
# Proxy provider swap — how can telemetry created before configure() flow into real providers afterwards?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** How does the SDK let code create spans/metrics/logs before `configure()` runs and have them (and their instruments) attach to the real providers once configured, including re-attach on every re-configure?

## ProxyTracerProvider / _ProxyTracer swap protocol
**Path/Symbol:** `logfire/_internal/tracer.py:ProxyTracerProvider.set_provider`, `_ProxyTracer.set_tracer` (`tracer.py:66-96`, `273-274`).
**Signature:** `set_provider(self, provider: SDKTracerProvider) -> None`; `_ProxyTracer(instrumenting_module_name: str, tracer: Tracer, provider: ProxyTracerProvider, is_span_tracer: bool)`.
**Data Shape:** `ProxyTracerProvider.tracers: WeakKeyDictionary[_ProxyTracer, Callable[[], Tracer]]` — each proxy tracer stores a **factory**, not just an instance; the factory re-resolves on every swap and consults `suppressed_scopes`.

### Decisive source
```python
def set_provider(self, provider: SDKTracerProvider) -> None:
    with self.lock:
        self.provider = provider
        for tracer, factory in self.tracers.items():
            tracer.set_tracer(factory())

def suppress_scopes(self, *scopes: str) -> None:
    with self.lock:
        self.suppressed_scopes.update(scopes)
        for tracer, factory in self.tracers.items():
            if tracer.instrumenting_module_name in scopes:
                tracer.set_tracer(factory())
```

**Flow:** `LogfireConfig.__init__` wraps `trace.NoOpTracerProvider()` in a `ProxyTracerProvider` (`config.py:1077`) so pre-configure spans are cheap no-ops → `_initialize()` builds the SDK provider and calls `set_provider` → every live `_ProxyTracer` is re-pointed at a fresh underlying tracer via its stored factory → `get_tracer` returns `SuppressedTracer()` whenever the scope name lands in `suppressed_scopes`. The identical pattern repeats for metrics (`metrics.py:ProxyMeterProvider.set_meter_provider` notifies every `_ProxyInstrument`) and logs (`logs.py:ProxyLoggerProvider.set_provider`), plus `set_min_level` pushes the level into all live `ProxyLogger`s.
**Invariant:** A tracer obtained before configure MUST become fully functional after configure without the caller holding it again — that is why factories live in a WeakKeyDictionary keyed by the tracer itself (no leaks, no stale instances). Suppressed scopes must be re-evaluated through the same factory path so suppression survives re-configuration.
**Probe:** `tests/test_configure.py` (`test_suppress_scopes` family) — suppressing a scope flips existing tracers to no-op without re-creating them.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "ProxyTracerProvider set_provider suppress_scopes", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the proxy-provider + factory-registry pattern wholesale — it is the mechanism that makes deferred configuration invisible to instrumented libraries. Adapt the OTEL-specific provider types to your tracing stack. Omit the Emscripten branches (`platform_is_emscripten` guards around thread-based processors).
