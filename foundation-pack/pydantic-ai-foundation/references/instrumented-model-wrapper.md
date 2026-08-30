<!-- capsule-v2 -->
# Instrumented model wrapper: non-idempent prepare + incremental message cache

## Source / Question
`pydantic_ai_slim/pydantic_ai/models/instrumented.py` — How does `InstrumentedModel` wrap a model with OpenTelemetry spans without corrupting request state, and how does it serialize the growing message history efficiently? A porter must know why the wrapped model is handed the ORIGINAL messages, not the prepared ones.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/models/instrumented.py` — `instrument_model` (47–55), `InstrumentationSettings` (58–196), `InstrumentedModel` (325–400), `_input_messages_json` (218–244), `handle_messages` (246–282), `aggregated_usage_attributes` (293–304), `record_metrics` (306–322).

## Signature
```python
def instrument_model(model: Model, instrument: InstrumentationSettings | bool) -> Model
class InstrumentedModel(WrapperModel):
    async def request(messages, model_settings, model_request_parameters) -> ModelResponse
    @asynccontextmanager
    async def request_stream(messages, model_settings, model_request_parameters, run_context=None)
```

## Data Shape
`InstrumentationSettings`: `tracer`, `meter`, `include_binary_content`, `include_content`, `include_model_request_parameters`, `version: Literal[2,3,4,5]`, `use_aggregated_usage_attribute_names`. `MessageJsonCache: dict[int, CachedMessageJson]` keyed by `id(message)`.

## Decisive source
`request()` (343–363) and `request_stream()` (365–400): the span's prepared context is for **span attributes only**. The wrapped model is handed the **original** `messages`/`model_request_parameters` because `prepare_request` is NOT idempotent — a second pass appends the prompted-output instructions a second time and re-walks an already-transformed JSON schema. `Instrumentation.wrap_model_request` and `FallbackModel.request` do the same. `request_stream` stamps `request_start = time.perf_counter()` BEFORE the wrapped model opens the stream so `time_to_first_chunk` spans from issue to first consumer-visible chunk, and calls `finish(response_stream.get(), time_to_first_chunk=...)` in `finally`.

## Flow / Invariant
1. `instrument_model` only wraps once (guard `not isinstance(model, InstrumentedModel)`); `True` → default `InstrumentationSettings()`.
2. **Never re-prepare**: the wrapper builds `ModelRequestContext` from the originals, opens the span, then calls `self.wrapped.request(messages, ...)` with the originals. A porter that passes the prepared messages will double-append instructions and re-walk schemas.
3. **Incremental history JSON** (`_input_messages_json`): with a `message_json_cache`, each message's fragment is cached keyed by `id(message)` and invalidated when `entry.parts is not message.parts` (parts identity, not content equality — a rebuilt message with new parts gets re-serialized). Fragments are concatenated `b'[' + b','.join(fragments) + b']'`, keeping per-request cost proportional to NEW messages. Entries for dropped messages are evicted (cache stays bounded by current history).
4. **Aggregated usage names**: `aggregated_usage_attributes` remaps `gen_ai.usage.*` → `gen_ai.aggregated_usage.*` when `use_aggregated_usage_attribute_names` so a backend summing span attributes doesn't double-count cumulative run usage against per-request spans.
5. **Metrics**: `record_metrics` records input/output token histograms, cost histogram (only when `price_calculation` present), and time-to-first-chunk.
6. Version 5 leaves deferral/approval spans UNSET (control flow, not errors); versions 2–4 emit a `PydanticAIDeprecationWarning`.

## Probe (direct test)
`tests/models/test_instrumented.py`: `test_instrumented_model` (:160), `test_input_messages_json_matches_whole_history_with_and_without_cache` (:367), `test_input_messages_json_refreshes_when_message_parts_are_replaced` (:392), `test_input_messages_json_evicts_entries_for_dropped_messages` (:410), `test_instrumented_model_stream` (:499), `test_instrumented_model_stream_break` (:597).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'InstrumentedModel request_stream'` → `models.instrumented.InstrumentedModel.request_stream` (366–400).

## Verdict
**Adopt** the wrapper pattern and the non-idempotent-prepare invariant (the load-bearing rule). **Adapt** the OTel attribute names/semconv versions to your observability backend; the incremental message-JSON cache is a reusable efficiency pattern for any growing-history serializer.
