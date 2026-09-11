<!-- capsule-v2 -->
# Stream endpoint typing — How do generator endpoints become JSONL/SSE streams, and how is the item type extracted from the return annotation?

**Source:** FastAPI MIT license `master@c3f316b7e814667e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** When does `-> Iterator[Item]` / `AsyncIterator[Item]` produce a streaming response, and which response_class combinations trigger JSONL vs SSE vs raw passthrough?

## Stream-mode detection at route build
**Path/Symbol:** `fastapi/dependencies/utils.py:_STREAM_ORIGINS/get_stream_item_type` (251–268) + `fastapi/routing.py:_populate_api_route_state` (1071–1123: is_sse/is_json flags, stream_item_field) + `get_request_handler` dispatch (520–704).
**Signature:** `get_stream_item_type(annotation) -> Any | None` (returns `type_args[0]` when origin ∈ {AsyncIterable, AsyncIterator, AsyncGenerator, Iterable, Iterator, Generator}, else None); route fields `is_sse_stream`, `is_json_stream`, `stream_item_type`.
**Data Shape:** `is_sse_stream = is_generator and lenient_issubclass(response_class, EventSourceResponse)`; `is_json_stream = is_generator and isinstance(response_class, DefaultPlaceholder)`; raw-generator branch handles explicit non-SSE response classes.

### Decisive source
```python
    is_generator = _is_async_gen_callable(route.dependant.call) or _is_gen_callable(route.dependant.call)
    ...
            stream_item = get_stream_item_type(return_annotation)
            if stream_item is not None and is_generator:
                # ServerSentEvent is excluded: it's a transport
                # wrapper, not a data model, so it shouldn't feed
                # into validation or OpenAPI schema generation.
                if (isinstance(response_class, DefaultPlaceholder)
                        or lenient_issubclass(response_class, EventSourceResponse)) \
                        and not lenient_issubclass(stream_item, ServerSentEvent):
                    route.stream_item_type = stream_item
                response_model = None
```

**Flow:** return-annotation resolution runs ONLY while response_model is still the `Default(None)` sentinel — an explicit `response_model=` suppresses stream typing → typed items get a serialization-mode `StreamItem_<unique_id>` ModelField used per-item by `_serialize_data` (validate → serialize_json) or embedded as SSE `data.contentSchema` in OpenAPI → untyped generators (`AsyncIterator` bare / no annotation) fall back to jsonable_encoder + json.dumps per item → `-> Response` annotations disable ALL derivation.
**Invariant:** (1) Streaming detection requires BOTH a generator callable AND a compatible response class — a plain `dict`-returning function with `EventSourceResponse` is NOT a stream. (2) `ServerSentEvent[...]` item types never become validation schemas; they're transport envelopes. (3) Per-item validation failures raise `ResponseValidationError` mid-stream — after headers are sent this surfaces as an aborted stream, not a 500 JSON body.
**Probe:** `tests/test_sse.py:test_sse_router_typed_openapi_schema`, `tests/test_stream_bare_type.py`, `tests/test_stream_json_validation_error.py`, `tests/test_stream_status_code.py`.
