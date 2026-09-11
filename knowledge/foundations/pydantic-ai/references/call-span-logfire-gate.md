<!-- capsule-v2 -->
# Call-span logfire gate — how do you make opt-in arg/return recording work with OR without logfire, without ever breaking the wrapped call?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter whose host may or may not have a rich instrumentation library (logfire) installed must decide whether to refuse an opt-in recording option that depends on it, how to open the call span on both backends, and whether a failing attribute write may affect the function's real return.

## Decoration-time refusal + dual-backend span opening
**Path/Symbol:** `pydantic_evals/pydantic_evals/online.py:OnlineEvalConfig.evaluate` RuntimeError gate (:566-571); `_default_call_span_name` (:382-389); `_open_call_span` (:392-412); record_return swallow in `_wrap_async` (:685-694) and `_wrap_sync` (:760-769).
**Signature:** `_open_call_span(msg_template: str, span_name: str | None, recorded_inputs: dict[str, Any] | None) -> Generator[Any]` (contextmanager).
**Data Shape:** Two backends behind one contextmanager: logfire's `logfire.span` (schema-serialized attributes) or raw OTel `tracer.start_as_current_span`. The span is the parent of every evaluator span and emitted event for that call.

### Decisive source
```python
# evaluate() — decoration time:
if (extract_args or record_return) and not _LOGFIRE_INSTALLED:
    raise RuntimeError(
        'extract_args and record_return require logfire to be installed for argument and '
        'return-value serialization. Install `pydantic-evals[logfire]` (or disable both '
        'options) to use them.'
    )

@contextmanager
def _open_call_span(msg_template, span_name, recorded_inputs):
    if _LOGFIRE_INSTALLED:
        attrs = recorded_inputs or {}
        with logfire_span(msg_template, _span_name=span_name, **attrs) as span:
            yield span
    else:
        tracer = trace.get_tracer('pydantic-evals')
        with tracer.start_as_current_span(span_name or msg_template) as span:
            yield span

# inside both wrappers, after the body returns:
if call_span.record_return:
    # Swallow attribute-set failures so an exotic return value (e.g. one whose repr
    # raises during logfire's JSON-schema serialisation) can't mask the function's
    # real return. `record_return=True` is opt-in for observability, not a contract
    # to fail the call.
    try:
        span.set_attribute('return', result)
    except Exception:  # pragma: no cover
        pass
```

**Flow:** Opting into `extract_args`/`record_return` without logfire raises at DECORATION time with a message that prescribes the exact extra (`pydantic-evals[logfire]`) — refused rather than silently degraded, because raw OTel would store opaque objects instead of schema-serialized values. With logfire absent but recording off, `_open_call_span` still opens a raw OTel span so evaluator events keep their parent; the default span name follows `@logfire.instrument`'s convention (`'Calling {module}.{qualname}'`). `msg_template` keeps its RAW form on the span (`logfire.msg_template`) while the rendered form lands in `logfire.msg`. `record_return` writes the return value as a span attribute inside a swallow-all try/except.
**Invariant:** Observability is opt-in and FAIL-SOFT: no span-attribute failure may alter, delay, or mask the wrapped function's return value or exception. The dependency gate is loud at decoration time, never a per-call degradation. Parenting must survive the absence of the rich library — the fallback backend exists precisely so evaluator events still nest under the call span.
**Probe:** `tests/evals/test_online.py::test_extract_args_without_logfire_raises` (:2258-2274) monkeypatches `_LOGFIRE_INSTALLED=False` and pins the decoration-time RuntimeError for BOTH options; `test_call_span_record_return` (:2194-2208) pins `attributes['return'] == 42`; `test_call_span_msg_template_and_span_name` (:2213-2230) pins raw-template-vs-rendered-msg split and `span_name` override; `test_sync_call_span_with_extract_args` (:2329-2345) pins the sync twin records both args and return.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_open_call_span _LOGFIRE_INSTALLED record_return set_attribute", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of online.py :382-412, :566-571, :685-694, :760-769 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the three-part contract: (1) refuse library-dependent options at decoration time with a prescribing error, (2) keep a raw-backend fallback so trace parenting survives without the rich library, (3) wrap every optional attribute write in a swallow-all guard so observability can never break the call. Adapt the `_LOGFIRE_INSTALLED` probe to your host's optional-dependency detection. Omit the logfire-specific `{arg=}` template rendering unless your host has an equivalent formatter. Coverage caveat: none — online.py read whole this pass.
