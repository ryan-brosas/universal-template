<!-- capsule-v2 -->
# Pending-span protocol — how can the UI render in-flight traces before their root span ends?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What exactly is emitted when a span starts, how is it linked back to the real span, and which processors see it?

## PendingSpanProcessor.on_start
**Path/Symbol:** `logfire/_internal/tracer.py:PendingSpanProcessor` (`tracer.py:339-404`) + wiring in `config.py:_initialize` (`config.py:1260-1274`, `1435-1461`).
**Signature:** `on_start(self, span: Span, parent_context: Context | None = None) -> None`; pending attributes add `logfire.span_type='pending_span'` and `logfire.pending_parent_id=str(real_parent_span_id_or_0)`.
**Data Shape:** synthetic ReadableSpan with a NEW span_id from the config id_generator but SAME trace_id/trace_flags; `start_time == end_time == real span's start_time`; parent = the REAL span context.

### Decisive source
```python
span_context = SpanContext(
    trace_id=real_span_context.trace_id,
    span_id=self.id_generator.generate_span_id(),
    is_remote=False,
    trace_flags=real_span_context.trace_flags,
)
attributes = {
    **attributes,
    ATTRIBUTES_SPAN_TYPE_KEY: 'pending_span',
    ATTRIBUTES_PENDING_SPAN_REAL_PARENT_KEY: trace_api.format_span_id(
        span.parent.span_id if span.parent else 0
    ),
}
start_and_end_time = span.start_time
pending_span = ReadableSpan(..., start_time=start_and_end_time, end_time=start_and_end_time, ...)
self.processor.on_end(pending_span)
```
Wiring: only processors whose `span_exporter` is a `TestExporter | RemovePendingSpansExporter | SimpleConsoleSpanExporter` are treated as having pending spans and get wrapped by a second `PendingSpanProcessor(multiprocessor-of-those)`; the docstring explains it intentionally is NOT a WrapperSpanProcessor to avoid double on_end/shutdown — "This processor is expected to contain processors which are already included elsewhere in the pipeline".
**Flow:** every recording span start (span_type None or 'span' only — logs/pending excluded) mints a zero-duration sibling that flows down the export pipeline immediately → UI shows a placeholder keyed by `pending_parent_id` → the real span later replaces/merges it (RemovePendingSpansExporter exists to strip pending spans from paths that shouldn't re-export them). Sampling re-check happens here because attribute-driven sampling is applied after start (`should_sample` pragma-comment).
**Invariant:** The new span_id MUST differ from the real one (else the merge key collides) while trace_id MUST match (trace assembly depends on it). Zero duration marks it as metadata, not a timing sample. Gate `span_type in (None,'span')` prevents infinite recursion (pending spans themselves must not spawn pendings).
**Probe:** `tests/test_pending_spans.py` — pins emission-per-start, attribute shape, and processor routing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "PendingSpanProcessor pending_span pending_parent_id RemovePendingSpansExporter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the shadow-event protocol for live-tail UX over any batched telemetry channel. Adapt the linkage attribute names and merge semantics of your backend. Omit the console/Test exporter routing if you have no equivalent dual-consumption problem.
