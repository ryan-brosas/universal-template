<!-- capsule-v2 -->
# API-model resilience kit — how do rate limits, retries, and prompt-size guards compose around provider calls?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What is the retry/backoff contract on ApiModel calls (which errors retry, how delays grow), and where do observations get truncated before they can blow the context?

## String-matched retry + exponential jitter
**Path/Symbol:** `src/smolagents/models.py:is_rate_limit_error` (:1194-1202), `ApiModel.__init__` retryer wiring (:1161-1183), RETRY_* constants (:38-41); `utils.py:RateLimiter` (:497-525), `Retrying` (:528-606), `truncate_content`/MAX_LENGTH_TRUNCATE_CONTENT (:254-265).
**Signature:** `Retrying(max_attempts=RETRY_MAX_ATTEMPTS=3, wait_seconds=RETRY_WAIT=60, exponential_base=2, jitter=True, retry_predicate=is_rate_limit_error, reraise=True)`; `RateLimiter.throttle()` sleeps to keep ≥ `60/rpm` spacing.
**Data Shape:** Retry predicate is STRING-based on str(exception).lower() containing "429" | "rate limit" | "too many requests" | "rate_limit"; delay recursion: `delay *= base * (1 + jitter*random())`.

### Decisive source
```python
# :571-579 — predicate-gated, attempt-bounded; reraise=True preserves original traceback:
except BaseException as e:
    should_retry = self.retry_predicate(e) if self.retry_predicate else False
    if not should_retry or attempt_number >= self.max_attempts:
        raise
...
delay *= self.exponential_base * (1 + self.jitter * random.random())
```

**Flow:** Every ApiModel.generate wraps its client call as `self.retryer(self.client.completion/chat_completion/converse, **kwargs)` after `self._apply_rate_limit()` throttle. 60s base wait ×2 growth with multiplicative jitter → attempts at t≈0/60-120/~180-360s. Because the predicate inspects message TEXT, it works across litellm/openai/boto3 error taxonomies without importing their exceptions — but it equally over-matches any exception whose message mentions "rate limit". Context protection is separate and layered: tool observations truncate at `utils.MAX_LENGTH_TRUNCATE_CONTENT=20000` chars head+tail halves with an explicit marker line (`truncate_content`), while sandbox print logs truncate separately at `max_print_outputs_length=50_000`.
**Invariant:** The two truncation budgets are independent because they guard different channels (step observation vs stdout capture); collapsing them either floods context or starves debugging. Retrying must re-read `self._last_call` AFTER sleeping so backoff and rate-limit spacing stack rather than collapse.
**Probe:** `tests/test_utils.py::TestRetrying-style cases around parse_json_blob` (:467+) plus models tests exercising retryer construction; live: fake client raising "Error code: 429" twice then succeeding → two sleeps logged by before_sleep_logger, result returned.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "Retrying is_rate_limit_error RateLimiter throttle", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt string-predicate retries only when you span providers with no shared exception base — otherwise prefer typed predicates. Adapt constants to your quota. Keep observation-vs-stdout truncation separate.
