<!-- capsule-v2 -->
# LogfireSpan lazy lifecycle — why is the OTel span not started until __enter__, and what breaks if you start it early?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** When exactly does the underlying span start/end relative to the context manager, and how do post-creation attribute writes stay consistent?

## LogfireSpan.__enter__/__exit__ state machine
**Path/Symbol:** `logfire/_internal/main.py:LogfireSpan` (`main.py:3122-3284`).
**Signature:** `__init__(self, span_name: str, otlp_attributes: dict, tracer: _ProxyTracer, json_schema_properties: JsonSchemaProperties, links: Sequence[tuple[SpanContext, Attributes]], span_kind: SpanKind = INTERNAL)`.
**Data Shape:** three mutable slots drive everything: `_added_attributes: bool`, `_token: Token | None`, `_span: _LogfireWrappedSpan | None`; `__getattr__` forwards everything else to the inner span only after it exists.

### Decisive source
```python
@handle_internal_errors
def _start(self):
    if self._span is not None:
        return
    self._span = self._tracer.start_span(
        name=self._span_name, attributes=self._otlp_attributes, links=self._links, kind=self._span_kind,
    )
...
@handle_internal_errors
def _end(self):
    if not self._span or not self._span.is_recording():
        return
    if self._added_attributes:
        self._span.set_attribute(ATTRIBUTES_JSON_SCHEMA_KEY, attributes_json_schema(self._json_schema_properties))
    self._span.end()
...
def __exit__(self, exc_type, exc_value, traceback) -> None:
    self._detach()
    if self._span and self._span.is_recording() and isinstance(exc_value, BaseException):
        self._span.record_exception(exc_value, escaped=True)
    self._end()
```

**Flow:** construction only stashes attributes (cheap, no OTel work — critical because `logfire.span(...)` is called even when the `with` body never executes) → `__enter__` starts the span THEN attaches it to OTEL context (token stored for detach) → `set_attribute` before start mutates `_otlp_attributes` (picked up by `_start`); after start it writes both the JSON-schema property and the live span → `__exit__` detaches FIRST (context restored before any processor runs), records escaping exceptions with `escaped=True`, ends, and flushes the JSON-schema sidecar ONLY if attributes were added post-construction.
**Invariant:** Start-before-attach ordering means child spans created in the body correctly parent to this span; detach-before-end ordering prevents processors from seeing stale context. `escaped=True` is what upgrades the exception to error status + error level (see `record_exception` in tracer.py). Re-entry of `_start`/`_attach` is idempotent via the None-checks.
**Probe:** `tests/test_main.py` — `with logfire.span(...)` lifecycle tests pin parenting, exception recording, and attribute timing.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "LogfireSpan _start _attach _detach record_exception escaped", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt lazy-start + eager-attribute-stash verbatim — starting eagerly wastes resources and mis-parents spans when the CM is unused. Adapt `NoopSpan.__getattr__` returning lambdas (the companion class at `main.py:3287`) which guarantees `span.foo(...)` calls on failed creation are silent no-ops. Omit the ReadableSpan inheritance trick if your span type is already duck-type friendly.
