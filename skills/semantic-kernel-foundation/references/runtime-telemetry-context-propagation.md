<!-- capsule-v2 -->
# Runtime telemetry context propagation — trace context rides inside the envelope and becomes links, never parents

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does a trace context travel inside a runtime envelope without coupling consumer spans to producer parents?

## EnvelopeMetadata + get_telemetry_* family
**Path/Symbol:** `python/semantic_kernel/agents/runtime/core/telemetry/propagation.py:EnvelopeMetadata` (lines 18–23), `get_telemetry_envelope_metadata` (39–50), `get_telemetry_grpc_metadata` (81–101), `get_telemetry_context` (108–128), `get_telemetry_links` (133–160).
**Signature:** `get_telemetry_envelope_metadata() -> EnvelopeMetadata`; `get_telemetry_context(metadata: TelemetryMetadataContainer) -> Context`; `get_telemetry_links(metadata) -> Sequence[Link] | None`; `TelemetryMetadataContainer = Optional[EnvelopeMetadata] | Mapping[str, str]`.
**Data Shape:** `EnvelopeMetadata` is a kw-only dataclass: `traceparent: str | None`, `tracestate: str | None`, `links: Sequence[Link] | None`. `TelemetryMetadataContainer` accepts either the dataclass or any Mapping (duck-typed via `__getitem__`) — the Mapping arm exists so gRPC/remote-call metadata dicts work unchanged.

### Decisive source
```python
def get_telemetry_envelope_metadata() -> EnvelopeMetadata:
    carrier: dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    return EnvelopeMetadata(traceparent=carrier.get("traceparent"), tracestate=carrier.get("tracestate"))

def get_telemetry_links(metadata):
    if metadata is None:
        return None
    if isinstance(metadata, EnvelopeMetadata):
        context = extract(_get_carrier_for_envelope_metadata(metadata))
    elif hasattr(metadata, "__getitem__"):
        context = extract(_get_carrier_for_remote_call_metadata(metadata))
    else:
        return None
    linked_span = get_current_span(context)
    span_context = linked_span.get_span_context()
    return [Link(span_context)]
```

**Flow:** Producer side: `send_message`/`publish_message` call `get_telemetry_envelope_metadata()` INSIDE their `trace_block("create", ...)` span (in_process_runtime.py 255/304), so the W3C propagator injects the CURRENT span's context into two plain string fields that are stored on the envelope and travel with it through the queue. Consumer side: `_process_send`/`_process_publish` pass `parent=message_envelope.metadata` into `trace_block`, which converts it via `get_telemetry_links` into OTel LINKS on the new span — the extracted remote context is deliberately NOT passed as the span's parent context (`context = None` in `trace_block`; the TODO in tracing.py acknowledges the choice). Result: producer and consumer spans are siblings joined by a link, not a parent/child chain — a queue boundary does not extend the producer's critical path. `get_telemetry_grpc_metadata` is the same inject step for Mapping-based transports (gRPC metadata dicts), merging over existing metadata without clobbering non-tracing keys.
**Invariant:** Trace context crosses the queue as DATA (two strings on the envelope), never as ambient asyncio context; consumers link, they do not parent. A None/unknown metadata container degrades to no links (empty Context / None), never an exception — except a genuinely unknown TYPE, which raises ValueError in `get_telemetry_context`.
**Probe:** `python/tests/unit/agents/runtime/test_runtime.py` lines 85–125: `MyTestExporter` (SpanExporter collecting `ReadableSpan`s) + `get_test_tracer_provider` (SimpleSpanProcessor) + the `tracer_provider` fixture (line 122–125) — the harness every span assertion in this file runs through; `test_register_receives_publish` (line 175) constructs `InProcessRuntime(tracer_provider=...)`, exercising the create→send→process span chain end to end.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "EnvelopeMetadata get_telemetry_envelope_metadata get_telemetry_links TraceContextTextMapPropagator extract", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: context-as-envelope-data with link-based consumer spans for any queue-mediated actor runtime — it keeps producer traces short and makes cross-queue causality explicit. Adapt: the Mapping duck-type arm if your transport metadata is already a dict (gRPC, HTTP headers). Omit: nothing — the pattern is small and self-contained; but do NOT copy the `context = None` TODO silently if you actually want parented consumer spans.
