<!-- capsule-v2 -->
# Fallback model chain with continuation pin + rewind

## Source / Question
`pydantic_ai_slim/pydantic_ai/models/fallback.py` — How does `FallbackModel` try models in sequence, route a suspended continuation to the pinned model, and rewind cleanly when the pinned continuation fails? A porter must get the fallback-on dispatch and the rewind/stamp semantics right.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/models/fallback.py` — `FallbackModel` (91–554), `_parse_fallback_on` (135–165), `_should_fallback` (189–199), `request` (229–318), `request_stream` (321–406), `_get_continuation_model` (453–461), `_pinned_continuation_model` (463–471), `_stamp_continuation` (491–501), `_stamp_replace_previous` (503–526), `_rewind_messages` (528–539), `_raise_fallback_exception_group` (541–554).

## Signature
```python
class FallbackModel(Model):
    def __init__(self, default_model, *fallback_models, fallback_on: FallbackOn = (ModelAPIError,))
    async def request(messages, model_settings, model_request_parameters) -> ModelResponse
```

## Data Shape
`FallbackOn = type[Exception] | tuple[...] | ExceptionHandler | ResponseHandler | Sequence[...]`. `_exception_handlers`/`_response_handlers` lists. Continuation pin lives in `metadata['__pydantic_ai__']['fallback_model_id']`. `_REPLACE_PREVIOUS_RESPONSE_KEY = 'replace_previous_response'` (duplicated literal, must match `_continuation`).

## Decisive source
`_parse_fallback_on` (135–165): handler type is auto-detected by inspecting the first parameter's type hint — if it's `ModelResponse`, it's a response handler; otherwise (incl. untyped lambdas) an exception handler. Empty fallback_on raises `UserError`. `request` (229–318): if the last message is a suspended response, the request routes to the pinned continuation model (bypassing the chain); if the pinned model raises a fallback-eligible error, `cancel_suspended_response` is best-effort called (so the abandoned server-side job doesn't keep billing), `_rewind_messages` strips the suspended response, and the normal chain is tried — the first successful response is stamped `replace_previous_response` so the merge treats it as fresh generation, not accumulate.

## Flow / Invariant
1. **Per-model profile**: each inner model has its own profile, so `prepare_messages` is re-run per model (`model.prepare_messages(messages, ...)`) — `FallbackModel.prepare_messages` itself returns the messages unchanged (dispatch applies each inner profile).
2. **fallback_on dispatch**: exceptions → `_exception_handlers`; responses → `_response_handlers`; `_should_fallback` awaits each handler (sync or async via `await_maybe`), first True triggers fallback.
3. **Response rejection cost accounting**: rejected responses are accumulated, their `cost` summed into `rejected_cost`, and added to the first successful response's usage so pricing isn't lost (`fill_response_cost` + `copy(usage)`` + `replace`).
4. **Continuation pin**: `_stamp_continuation` writes `model.model_id` into `metadata['__pydantic_ai__']['fallback_model_id']` for stateless routing; `_pinned_continuation_model` resolves it by matching `m.model_id`.
5. **Rewind**: `_rewind_messages` pops the trailing suspended `ModelResponse`; `_stamp_replace_previous` sets the transient `replace_previous_response` marker so a same-model rewind (only `provider_response_id` differs) is classified as `'replace-new'` not `'accumulate'` — otherwise the abandoned suspended parts get duplicated ahead of the fresh turn. The marker is popped after being honored.
6. **Streaming stamp timing asymmetry**: in `request_stream`, the continuation pin is stamped **after** `yield` (state only final once the stream is consumed) BUT the replace marker must land on `metadata` **before** `yield` — the streamed composite resolves `_segment_offset` via `merge_mode` on the first reindexable event, so a late replace stamp would reindex against a stale `'accumulate'` verdict.
7. `_raise_fallback_exception_group` wraps all exceptions + a `ResponseRejected(len(rejected))` into a `FallbackExceptionGroup`.

## Probe (direct test)
`tests/models/test_fallback.py`: `test_first_successful` (:141), `test_first_failed` (:168), `test_all_failed` (:540), `test_response_handler_triggered` (:1413), `test_response_handler_rejected_cost_counts_toward_limit` (:1452), `test_mixed_exception_and_response_handlers` (:1549), `test_fallback_continuation_failure_rewinds_to_clean_history` (:2363), `test_fallback_same_model_rewind_recovery_does_not_duplicate` (:2656), `test_fallback_streaming_same_model_rewind_recovery_does_not_duplicate` (:2720).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'FallbackModel request fallback_on'` → `models.fallback.FallbackModel._parse_fallback_on` (135–165) + `.request` (229–318).

## Verdict
**Adopt** the fallback-chain contract (handler auto-detection, per-model profile re-prepare, response-rejection cost carry). **Adapt** the continuation-pin/rewind machinery to your suspend/resume model — the before-yield vs after-yield stamp asymmetry is the subtle part a porter would get wrong.
