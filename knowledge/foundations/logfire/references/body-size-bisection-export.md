<!-- capsule-v2 -->
# Body-size bisection export — how does an oversized batch still get delivered when the backend rejects its size?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** How do exporters cooperate to split a batch whose serialized payload exceeds the limit, and why is the split recursive rather than iterative?

## BodySizeCheckingOTLPSpanExporter + RetryFewerSpansSpanExporter
**Path/Symbol:** `logfire/_internal/exporters/otlp.py:BodySizeCheckingOTLPSpanExporter._export` (`otlp.py:42-64`) + `RetryFewerSpansSpanExporter.export` (`otlp.py:282-300`).
**Signature:** `_export(self, serialized_data: bytes, *args, **kwargs)` raising `BodyTooLargeError(size, max_size)`; `export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult`.
**Data Shape:** `max_body_size = 5MB` (chosen below backend limits for latency/reliability, not at the boundary); `_current_num_spans` smuggled from the outer `export()` call into `_export` per batch.

### Decisive source
```python
def _export(self, serialized_data, *args, **kwargs):
    if self._current_num_spans > 1 and len(serialized_data) > self.max_body_size:
        raise BodyTooLargeError(len(serialized_data), self.max_body_size)
    return super()._export(serialized_data, *args, **kwargs)
...
def export(self, spans):                     # RetryFewerSpansSpanExporter
    try:
        return super().export(spans)
    except BodyTooLargeError:
        half = len(spans) // 2
        assert half > 0                      # single-span batches must NOT raise upstream
        res1 = self.export(spans[:half])
        res2 = self.export(spans[half:])
        if res1 is not SpanExportResult.SUCCESS or res2 is not SpanExportResult.SUCCESS:
            return SpanExportResult.FAILURE
        return SpanExportResult.SUCCESS
```

**Flow:** BatchSpanProcessor hands N spans to `export` → count recorded → serialization attempted → if >1 span AND >5MB the low-level exporter raises instead of sending → the wrapping exporter bisects recursively (halves may themselves be too large, recursing again) → results combined with identity comparison `is not SUCCESS`. A single oversized span falls through to the real send attempt (backend decides; comment: splitting can't help).
**Invariant:** The `>1 span` gate is essential — a one-span batch that raises BodyTooLargeError would infinitely recurse on `assert half > 0`. Identity (`is not`) comparison of SpanExportResult matters because it's not value-equal-safe. Decoration order in `_initialize` is `QuietSpanExporter(RetryFewerSpansSpanExporter(BodySizeChecking…(OTLP)))` — Quiet catches RequestException OUTSIDE bisection so partial-split failures don't dump tracebacks but still return FAILURE.
**Probe:** `tests/test_otlp_exporter.py` (`test_retry_fewer_spans` family) — pins split-and-retry on oversized payloads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "BodyTooLargeError RetryFewerSpansSpanExporter max_body_size", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the exception-signal + recursive-halving protocol for any size-limited transport; keep the single-item guard. Adapt the 5MB constant and span-count plumbing to your exporter interface. Omit the OTLP protobuf specifics.
