<!-- capsule-v2 -->
# Invocation telemetry wrapper — span, sensitive-data gate, histogram-in-finally, error re-raise

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Where do tracing spans, sensitive-argument redaction, duration metrics, and error status attach so every function invocation is uniformly observable?

## KernelFunction.invoke / invoke_stream wrapper
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function.py:KernelFunction.invoke` (lines 240–297), `.invoke_stream` (308–379), `._handle_exception` (396–410).
**Signature:** `async def invoke(self, kernel: "Kernel", arguments: "KernelArguments | None" = None, metadata: dict[str, Any] | None = None, **kwargs) -> "FunctionResult | None"`; `def _handle_exception(self, current_span: trace.Span, exception: Exception, attributes: dict[str, str]) -> None`.
**Data Shape:** Wraps abstract `_invoke_internal`/`_invoke_internal_stream` inside a `FunctionInvocationContext`; records `invocation_duration_histogram` / `streaming_duration_histogram` tagged with `MEASUREMENT_FUNCTION_TAG_NAME = fully_qualified_name`.

### Decisive source
```python
with function_tracer.start_as_current_span(tracer, self, metadata) as current_span:
    if function_tracer.are_sensitive_events_enabled():
        current_span.set_attribute(TOOL_CALL_ARGUMENTS, arguments.dumps())
    ...
    try:
        stack = kernel.construct_call_stack(FilterTypes.FUNCTION_INVOCATION, self._invoke_internal)
        await stack(function_context)
        ...
        return function_context.result
    except Exception as e:
        self._handle_exception(current_span, e, attributes)
        raise e
    finally:
        duration = time.perf_counter() - starting_time_stamp
        self.invocation_duration_histogram.record(duration, attributes)

def _handle_exception(self, current_span, exception, attributes):
    attributes[ERROR_TYPE] = type(exception).__name__
    current_span.record_exception(exception)
    current_span.set_attribute(ERROR_TYPE, type(exception).__name__)
    current_span.set_status(trace.StatusCode.ERROR, description=str(exception))
```

**Flow:** Before context construction the module calls `_rebuild_function_invocation_context()` — a pydantic `model_rebuild()` with deferred imports that resolves forward references (`Kernel`, `FunctionResult`) broken by circular imports. Then: OTel span → sensitive-events gate decides whether raw arguments/results ever land on the span → filter-stack call → success logging; on failure `_handle_exception` decorates the span and the caller **re-raises** (telemetry never swallows); `finally` records duration in both paths.
**Invariant:** Duration is recorded exactly once per invocation even when the filter stack raises; sensitive payloads are emitted only under `are_sensitive_events_enabled()`; exceptions keep propagating after being recorded.
**Probe:** `python/tests/unit/functions/test_kernel_function_from_method.py::test_function_invocation_filters_streaming` (406–448) proves filters see the live stream inside this wrapper; cancellation swallowing lives one level up in `Kernel.invoke` (`OperationCancelledException` → log + `None`, kernel.py 192–213; tests 153–171).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "are_sensitive_events_enabled invocation_duration_histogram _handle_exception", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapper skeleton (span + gate + finally-histogram + record-and-reraise + model_rebuild hook) for any function-runner with OTel ambitions. Adapt attribute names and the sensitivity gate to your telemetry config surface. Omit the pydantic rebuild dance if your host has no circular-import pressure.
