<!-- capsule-v2 -->
# Tracer — NoOp/OpenTelemetry spans behind one ABC

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** how do you add observability spans through a whole pipeline while keeping zero telemetry a valid default?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/tracer.py` (193 lines): `TracerSpan` (ABC :33) — `add_attributes` (:37), `set_status` (:42), `record_exception` (:47); `Tracer` (ABC :52) — `start_span(name)` returning a context manager; `NoOpSpan` (:61), `NoOpTracer` (:74); `OpenTelemetrySpan` (:83), `OpenTelemetryTracer` (:126, span_prefix 'graphiti'); `create_tracer` factory (:159).
**Signature:** `with tracer.start_span('name') as span: span.add_attributes({...}); span.set_status('ok'|'error', desc)` — the same code runs with or without OTel.
**Data Span:** spans carry attributes, status + optional description, and recorded exceptions; prefix namespaces all span names.
**Data Shape:** `create_tracer(otel_tracer=None)` returns `OpenTelemetryTracer` when given an OTel tracer else `NoOpTracer`.

### Decisive source
```ts
class Tracer(ABC):
    def start_span(self, name: str) -> AbstractContextManager[TracerSpan]: ...
class OpenTelemetryTracer(Tracer):
    def __init__(self, tracer: Any, span_prefix: str = 'graphiti'): ...
    def start_span(self, name):
        # wraps otel tracer.start_as_current_span(f'{prefix}.{name}')
def create_tracer(otel_tracer=None, span_prefix='graphiti') -> Tracer:
    return OpenTelemetryTracer(otel_tracer, span_prefix) if otel_tracer else NoOpTracer()
```

**Flow:** pipeline methods accept an optional tracer (LLMClient has `set_tracer`) → every phase wraps its work in `start_span` → attributes/status/exceptions land on the span → with no OTel configured the NoOp implementations make it all free.
**Invariant:** instrumentation is ambient (works with zero config); span names are prefixed (`prefix.rstrip('.')`); every OTel span method swallows its own exceptions so tracing can never break the traced operation — `OpenTelemetryTracer.start_span` even yields a NoOpSpan if the OTel call itself throws; the trace shape is identical whether backed by OTel or NoOp; search phases use `_trace_phase` helpers so phase timing is consistent.
**Probe:** no dedicated tracer unit test exists at `main@401c59a6` (coverage caveat — verified by whole-file read; NoOp path is exercised implicitly by every LLM-client test since `LLMClient.__init__` defaults to NoOpTracer).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "Tracer start_span NoOpTracer OpenTelemetryTracer create_tracer set_status", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-class tracer ABC (NoOp default, OTel adapter) with context-manager spans and a factory; adapt span naming/prefix to host.
