<!-- capsule-v2 -->
# Error taxonomy — where does error classification happen, and why must it be a late re-labeling not an early throw?

**Source:** agno Apache-2.0 `main@9644f22982ae017eaa4ad85c561d927d9ac03119`; Codebase Memory `ext-agno`. **Question:** How do untyped provider errors become rate-limit/context-window errors without every call site pre-classifying?

## ModelProviderError.classify
**Path/Symbol:** `libs/agno/agno/exceptions.py:123` (`ModelProviderError.classify`; pattern table :96-110; subclasses :157/:167).
**Signature:** `@classmethod classify(cls, error: ModelProviderError) -> ModelProviderError`.
**Data Shape:** base carries `message` + `status_code` (default 502) + `model_name/model_id` + wire fields `type`/`error_id`; classification inputs are status codes {429, 529} and 12 lowercase substring patterns.

### Decisive source
```python
CONTEXT_WINDOW_PATTERNS = [
    "context_length_exceeded", "context window", "maximum context length",
    "token limit", "max_tokens", "too many tokens", "payload too large",
    "content_too_large", "request too large", "input too long",
    "prompt is too long", "prompt too long", "exceeds the model",
]

@classmethod
def classify(cls, error):
    if isinstance(error, (ModelRateLimitError, ContextWindowExceededError)):
        return error                                   # already classified — idempotent
    if error.status_code in {429, 529}:                # 529 = Anthropic OverloadedError
        return ModelRateLimitError(...)
    if any(p in str(error.message).lower() for p in cls.CONTEXT_WINDOW_PATTERNS):
        return ContextWindowExceededError(...)         # message wins over status code
    return error
```
Surrounding family: `RunCancelledException` (type/error_id = run_cancelled_error), guardrail pair `InputCheckError`/`OutputCheckError` (carry `check_trigger`, become team error events WITHOUT retry), `RetryableModelProviderError` dataclass (guidance carrier), `ComponentRehydrationError` (strict deserialization refusal), `RunNotFoundError(RuntimeError)`→404 / `RunNotContinuableError(ValueError)`→409 mapping contract.

**Flow:** any provider adapter wraps failures into generic `ModelProviderError` → consumers (`_invoke_with_retry`, `get_fallback_models`) call `classify()` at DECISION time → subclass identity then drives retryability/fallback-list choice.
**Invariant:** (1) Classification is IDEMPOTENT and late — adapters stay dumb; the consumer classifies when it can act on the answer. (2) For context-window, the MESSAGE beats the status code (many providers emit 400 for overflow). (3) 529 is deliberately grouped with 429 as fallback/retry-legitimate. (4) The same pattern list is reused verbatim in `_is_retryable_error` — one table, two consumers.
**Probe:** live-executed at pin via probe battery: classify(429)→ModelRateLimitError ✓, classify("maximum context length",400)→ContextWindowExceededError ✓, idempotence on already-typed errors ✓; upstream `tests/unit/test_fallback.py::test_get_fallback_models_classifies_429` executed GREEN.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agno", query: "ModelProviderError classify CONTEXT_WINDOW_PATTERNS", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt late idempotent classification with the message-over-status precedence and the 529 carve-out; adapt the pattern list to your providers' phrasing; omit agno's specific HTTP-mapping exceptions. Direct tests exist and were executed green.
