<!-- capsule-v2 -->
# Attribute-driven tail sampling — how can per-span sample rates travel on the span itself and be enforced post-hoc?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** How does the `logfire.sample_rate` attribute deterministically decide span inclusion, and where is it checked?

## should_sample + get_sample_rate_from_attributes
**Path/Symbol:** `logfire/_internal/tracer.py:should_sample` (`tracer.py:407-419`) + enforcement in `_ProxyTracer.start_span` (`tracer.py:304-314`) and `PendingSpanProcessor.on_start` (`tracer.py:367-372`).
**Signature:** `should_sample(span_context: SpanContext, attributes: Mapping) -> bool`; rate resolution: instance `_sample_rate` → attribute pop → omit.
**Data Shape:** threshold math `span_id <= round(sample_rate * 2**64)`; sampled-out spans become NonRecordingSpan keeping trace/span ids with SAMPLED flag cleared.

### Decisive source
```python
def should_sample(span_context, attributes) -> bool:
    sample_rate = get_sample_rate_from_attributes(attributes)
    return sample_rate is None or span_context.span_id <= round(sample_rate * 2**64)
```
In `_ProxyTracer.start_span`: after the real span started,
```python
if not should_sample(span.get_span_context(), attributes):
    span = trace_api.NonRecordingSpan(SpanContext(
        trace_id=..., span_id=..., is_remote=False,
        trace_flags=trace_api.TraceFlags(span.get_span_context().trace_flags & ~TraceFlags.SAMPLED)))
```
Attribute plumbing (main.py `_span`/`log`, lines ~259/803): instance-level `Logfire(sample_rate=x)` overrides everything; else `ATTRIBUTES_SAMPLE_RATE_KEY` is POPPED from user attributes (so users can set it inline); stored only when `sample_rate is not None and sample_rate != 1`.
**Flow:** user sets rate via instance, context (`with_tags`-style instances), or attribute → span starts normally → deterministic span-id-vs-threshold check downgrades to non-recording (children still parent correctly because ids persist) → PendingSpanProcessor re-checks "because currently our own sampling is only checked after the span has started" (Linear PYD-552 noted in-source).
**Invariant:** Determinism (same id ⇒ same decision) is what makes partial traces coherent across services. The SAMPLED-bit clear keeps downstream OTEL exporters from re-including it. Rate=1 must not be written as an attribute (noise).
**Probe:** `tests/test_sampling.py` — pins threshold semantics and downgrade shape.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "should_sample ATTRIBUTES_SAMPLE_RATE_KEY NonRecordingSpan TraceFlags", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt span-id-threshold sampling with attribute transport — it composes with any head/tail machinery. Adapt threshold bit-width to your id size. Omit the pending-span re-check only if your sampler runs before start.
