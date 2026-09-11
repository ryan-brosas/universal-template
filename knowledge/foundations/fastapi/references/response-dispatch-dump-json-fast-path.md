<!-- capsule-v2 -->
# Response dispatch ladder + dump_json fast path — How is the endpoint's return value turned into a Response, and when does serialization skip the Python dict?

**Source:** FastAPI MIT license `master@c3f316b7e8ee81e03a7330d00ee61e45c`; Codebase Memory `ext-fastapi`. **Question:** In what precedence order are SSE / JSONL / generator / raw-Response / model returns handled, and when can serialization go straight to JSON bytes via Pydantic's Rust core?

## get_request_handler dispatch
**Path/Symbol:** `fastapi/routing.py:get_request_handler.app` (dispatch 491–755) + `serialize_response` (301–341) + `_build_response_args` (357–372).
**Signature:** `serialize_response(*, field, response_content, include, exclude, by_alias=True, exclude_unset=False, exclude_defaults=False, exclude_none=False, is_coroutine=True, endpoint_ctx=None, dump_json=False) -> Any`.
**Data Shape:** dispatch flags fixed at route build: `is_sse_stream = generator and response_class is EventSourceResponse`; `is_json_stream = generator and response_class is DefaultPlaceholder`; raw-generator branch for explicit StreamingResponse-style classes; else normal call.

### Decisive source
```python
                    use_dump_json = response_field is not None and isinstance(
                        response_class, DefaultPlaceholder)
                    content = await serialize_response(
                        field=response_field, response_content=raw_response,
                        include=..., by_alias=..., is_coroutine=is_coroutine,
                        endpoint_ctx=endpoint_ctx, dump_json=use_dump_json)
                    if use_dump_json:
                        response = Response(content, media_type="application/json", **response_args)
```
with `serialize_response` choosing `field.serialize_json` (bytes) vs `field.serialize` (python obj → later json.dumps), raising `ResponseValidationError(errors, body=response_content, endpoint_ctx=ctx)` on validation failure — the error now carries file/line context from `_extract_endpoint_context`.

**Flow:** SSE branch wires a producer task + keepalive inserter through anyio memory streams (see sse-keepalive capsule) → JSONL branch appends `\n` per validated item with `await anyio.sleep(0)` after each yield so cancellation can be delivered even when the consumer never awaits (`#14680`) → bare generator + explicit response class streams raw chunks → returned `Response` instances pass through UNCHANGED except adopting solved background tasks when none set → model/dict returns validate against `response_field` then render. Every rendered branch extends headers with `solved_result.response.headers.raw` so dependency-set headers survive; status resolution prefers explicit `status_code`, then dependency-mutated `solved_result.response.status_code`; bodies blanked for 204/205/304 via `is_body_allowed_for_status_code`.
**Invariant:** (1) The fast path requires BOTH a typed response field AND an un-overridden default response class — a custom response class forces the dict+encoder path because its renderer owns encoding. (2) Returning a `Response` bypasses response-model filtering BY DESIGN; validation only guards non-Response values. (3) Sync endpoints' `serialize_response` runs in the threadpool (`is_coroutine=False`).
**Probe:** `tests/test_response_model_as_return_annotation.py` (annotation-derived models), `tests/test_stream_json_validation_error.py`, `tests/test_stream_cancellation.py` (checkpoint requirement), plus per-tutorial suites pin each rung.
