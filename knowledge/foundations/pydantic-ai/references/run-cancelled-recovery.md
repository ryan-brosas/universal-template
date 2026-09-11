<!-- capsule-v2 -->
# RunCancelled.from_cancellation: partial-state recovery

## Source / Question
`pydantic_ai_slim/pydantic_ai/exceptions.py` — How does pydantic-ai let a caller recover partial run state from an EXTERNAL `CancelledError` (or the `TimeoutError` from `asyncio.timeout()`/`wait_for()`), while keeping external cancels propagating? A porter must know the exception-chain traversal and the first-party-vs-external distinction.

## Path / Symbol
`pydantic_ai_slim/pydantic_ai/exceptions.py` — `RunCancelled` (268–~380), `RunCancelled.from_cancellation` (322–~380), `_RUN_CANCELLED_ATTR = '_pydantic_ai_run_cancelled'` (265), `_attach_to` (313–315).

## Signature
```python
class RunCancelled(AgentRunError):
    @classmethod
    def from_cancellation(cls, exc: BaseException) -> RunCancelled | None
```

## Data Shape
`RunCancelled` carries `messages`, `new_message_index`, `usage`, `metadata`, `run_id`, `conversation_id` — the partial run state. `_RUN_CANCELLED_ATTR` is attached to a `BaseException` via `_attach_to`.

## Decisive source
`from_cancellation` (322–~380): BFS over the exception's `__cause__`/`__context__` chain (cycle-safe via `visited` id set). Returns the first `RunCancelled` found, either as the exception itself or via the attached `_RUN_CANCELLED_ATTR`. This works with the `TimeoutError` raised by `asyncio.timeout()`/`wait_for()`, whose chain contains the original `CancelledError`. Python 3.11+ preserves the exception instance across `await task`; 3.10 recreates `CancelledError` but chains the original via `__context__` (attached only to the first await, so later awaits see an unchained exception — `capture_run_messages()` is the fallback when only history is needed).

## Flow / Invariant
1. **External cancels keep propagating**: catch `CancelledError`, call `from_cancellation(exc)` to capture state, then RE-RAISE — only a first-party `RunCancelled` is yours to consume; external cancels must keep propagating for timeouts/task-groups to tear down correctly.
2. **Uniform handling**: passing a `RunCancelled` directly returns the same instance, unifying first-party and external paths.
3. **Partial state preserved**: everything completed before cancellation — partial stream response, finished tool results — is in `all_messages()`; pass it as `message_history` to resume; unfinished tool calls are closed out with synthesized `outcome='interrupted'` returns.
4. **Terminal**: capability hooks may observe cancellation and clean up but cannot recover a cancelled run into success.

## Probe (direct test)
`tests/test_run_cancellation.py`: `test_from_cancellation_identity_and_none` (:992), `test_from_cancellation_cycle_safe` (:1003), `test_direct_await_cancellation_carries_run_cancelled_on_all_versions` (:877), `test_from_cancellation_through_asyncio_timeout` (:909), `test_run_cancelled_pickle_round_trip` (:335).

## Retrieve
`search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'RunCancelled from_cancellation'` → `exceptions.RunCancelled.from_cancellation` (322–~380).

## Verdict
**Adopt** the attach-and-traverse pattern (stamp partial state onto the exception, recover it by walking `__cause__`/`__context__`). **Adapt** the message-history payload to your run state; the "capture then re-raise external cancels" rule is the invariant a porter must not violate.
