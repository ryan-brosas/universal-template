<!-- capsule-v2 -->
# FallbackCompaction strategy chains: typed failure-gated fallback with fresh-input replay

## Source / Question
`pydantic_ai_harness/compaction/_fallback_compaction.py` (66L whole file) @ `main@f971198` — When a compaction strategy can fail (a summarizer model errors), how do you chain a cheaper deterministic backup WITHOUT swallowing programming errors or cancellation, and without letting a failed attempt's input mutations poison the next attempt?

## Path / Symbol
`compaction/_fallback_compaction.py` — `FallbackCompaction` dataclass (:17–47), `compact` (:49–62), `_is_exception_type` (:65–66).

## Signature
```python
@dataclass
class FallbackCompaction(Generic[AgentDepsT]):
    fallback_chain: Sequence[CompactionStrategy[AgentDepsT]]
    fallback_on: tuple[type[Exception], ...] = (ModelAPIError, FallbackExceptionGroup)
    async def compact(self, messages: list[ModelMessage], ctx: RunContext[AgentDepsT]) -> list[ModelMessage]
    def with_focus(self, focus: str) -> FallbackCompaction[AgentDepsT]   # forwards focus only to SupportsFocus strategies
```

## Data Shape
`fallback_on` defaults to model-API failures INCLUDING an exhausted `FallbackModel` (`ModelAPIError`, `FallbackExceptionGroup`) — so programming errors pass through and abort. Construction validates non-empty chain, non-empty `fallback_on`, every entry an `Exception` subclass (`_is_exception_type`: `isinstance(v, type) and issubclass(v, Exception)`).

### Decisive source
```python
last_error: Exception | None = None
for strategy in self.fallback_chain:
    try:
        return await strategy.compact(list(messages), ctx)   # fresh COPY of the original objects
    except self.fallback_on as error:
        last_error = error
assert last_error is not None
raise last_error                                          # LAST matching failure re-raised
```

**Flow:** try strategy → success returns immediately → matching failure records and falls to next → all fail ⇒ re-raise the LAST matching exception; non-matching exceptions propagate on first occurrence.
**Invariant:** each attempt receives a fresh `list(messages)` copy containing the ORIGINAL message objects — a mutating failed strategy cannot corrupt later attempts; `BaseException` subclasses (cancellation!) are structurally uncatchable because entries must derive from `Exception`.

## Probe (direct test)
`tests/compaction/test_compaction.py::TestFallbackCompaction` — `test_fallback_receives_fresh_original_list` (:481–495, a strategy clears `messages` then raises; second still gets originals), `test_reraises_last_failure` (:497), `test_non_matching_error_does_not_fallback` (:505), `test_cancellation_does_not_fallback` (:515, CancelledError propagates, second not called), `test_fallback_model_exhaustion_uses_next_strategy` (:524, real Agent + exhausted FallbackModel), construction matrix :446–461 (empty chain / empty fallback_on / non-exception entry all ValueError), `with_focus` forwarding :533–554.

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'FallbackCompaction' --detail ids
# -> pydantic-ai-harness.pydantic_ai_harness.compaction._fallback_compaction.FallbackCompaction
```

## Verdict
**Adopt** the typed-exception fallback gate + per-attempt fresh-list copy for ANY strategy-chain runner. **Adapt** `fallback_on` to your domain's expected-failure types. **Omit** nothing — the file is fully portable.
