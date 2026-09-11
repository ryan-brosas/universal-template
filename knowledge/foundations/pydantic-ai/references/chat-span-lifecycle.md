<!-- capsule-v2 -->
# Chat span lifecycle: prepare-inside, metrics-after-close, versioned span names

## Source / Question
`pydantic_ai_slim/pydantic_ai/_instrumentation.py::open_model_request_span` + `InstrumentationNames` (+ capability wiring in `capabilities/instrumentation.py`) — What is the correct ORDER of operations around a model-request span so telemetry is complete but never double-counted, and how do span names/attributes stay stable across instrumentation-version migrations? A porter that records token metrics inside the span (or re-prepares the request outside it) corrupts backends that aggregate from span attributes.

## Path / Symbol
`_instrumentation.py` — `open_model_request_span` (444–544), `_FinishModelRequestSpan` protocol (434–441), `finish` closure (501–539), `provider_attributes` (284–303), `model_attributes` (306–310), `model_settings_attributes` (336–343), `build_tool_definitions` (370–396), `response_attributes` (399–420), `response_price_calculation` (423–431), `get_instructions` (580–640), `InstrumentationNames.for_version` (657–733), `time_to_first_chunk_ctx` ContextVar (78–87); wiring: `capabilities/instrumentation.py::wrap_model_request` (283–319).

## Signature
```python
@contextmanager
def open_model_request_span(settings, request_context, *, message_json_cache=None)
    -> Generator[tuple[_FinishModelRequestSpan, ModelRequestContext], ...]
class InstrumentationNames:
    @classmethod
    def for_version(cls, version: int) -> Self  # v2 legacy names vs v3+ genai semconv
```

## Data Shape
Yields `(finish, prepared_request_context)` — prepared settings/parameters are built INSIDE the CM (`model.prepare_request`, :468–473) so the caller never prepares twice; `dataclasses.replace(request_context, …)` carries them. Span name `'chat {model_name}'`, kind CLIENT; attributes: operation name, model attrs (`gen_ai.provider.name` + deprecated `gen_ai.system` both set :287–288), baggage trio, optional `model_request_parameters` JSON gated by `include_model_request_parameters` + a `logfire.json_schema` hint, OTel-spec `gen_ai.tool.definitions` (withheld tools EXCLUDED — recording a hidden description would leak sensitive telemetry the model never saw, :384–388), `gen_ai.request.{max_tokens,top_p,seed,temperature,presence_penalty,frequency_penalty}` (only numeric values).

## Decisive source
The ordering contract, pinned in comments:
1. **Metrics recorded AFTER the span closes** (:493–500, :541–544): `record_metrics` is captured as a nonlocal and invoked in the outer `finally` — "so observability backends that aggregate metrics from span attributes don't double-count."
2. **Cost computed BEFORE the `is_recording()` gate** (:520–525): "so `_record_metrics` always emits cost data, even when the span is dropped by sampling."
3. **FallbackModel attribute merge** (:506–509): `attributes.update(getattr(span, 'attributes', {}))` — the fallback chain mutates span attributes via `get_current_span()` mid-flight; finish re-reads them so request/system reflect the model that ACTUALLY answered.
4. **TTFT via ContextVar, not parameter plumbing** (:78–87): streaming handler sets `time_to_first_chunk_ctx` in the same task; capability reads `.get()` after `await handler(...)`; "a value can't outlive its request" because the graph spawns a fresh task per streaming request. Non-streaming reads None.
5. **Version ladder**: v2 → `'agent run'`/`'running tool'`/`tool_arguments`; v3+ → `invoke_agent {name}`/`execute_tool {name}`/`gen_ai.tool.call.*`. ClassVar attrs (`pydantic_ai.tool.deferral.name/metadata`, `pydantic_ai.tool.failure_stage`) are version-independent.

## Flow / Invariant
Capability side (`wrap_model_request`): stash `_last_messages = request_context.messages` FIRST (UserPromptNode replaces list refs — ctx.messages goes stale on error paths) → open span → record `_last_model_request_parameters` (lets end-of-run instructions use canonical sorted instruction_parts instead of history fallback) → diff formatted instructions vs previous to set `_variable_instructions` → `response = await handler(request_context)` → `finish(response, time_to_first_chunk=time_to_first_chunk_ctx.get())`.
`get_instructions` history-fallback rule (:600–638): walk reversed for last TWO ModelRequests — if the most recent consists ONLY of tool-return/retry-prompt parts (the synthetic "mock" request generated for result tools), take instructions from the second-most-recent.
End-of-run attributes (`_run_span_end_attributes`, cap-instrumentation :236–277): full `pydantic_ai.all_messages` OTel dump, aggregated usage attrs, `logfire.json_schema` marking array-typed string attrs.

## Probe (direct test)
`tests/models/test_instrumented.py`: `test_instrumented_model` (:160), `test_instrumented_model_stream` (:499, TTFT stamping), `test_instrumentation_settings_rejects_removed_version` (:481), `test_instrumentation_settings_warns_for_deprecated_versions` (:486). `tests/test_logfire.py` pins span names/attribute shapes end-to-end with the capability attached; `tests/models/test_fallback.py` pins the fallback attribute-merge path.

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'open_model_request_span record_metrics InstrumentationNames'`

## Verdict
**Adopt** the ordering contract verbatim — prepare-once inside the CM, cost-before-sampling-gate, metrics-after-close, stale-listener merge — it is backend-agnostic discipline. **Adopt** the ContextVar TTFT channel whenever producer and consumer share a task but not a call stack. **Adapt** names/versions via a small `for_version` table rather than scattered conditionals.
