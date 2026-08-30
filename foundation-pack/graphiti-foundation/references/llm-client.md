<!-- capsule-v2 -->
# LLM base client — transient-error taxonomy, sentinel preamble, input cleaning

**Source:** graphiti MIT `main@401c59a6`; Codebase Memory `graphiti`. **Question:** which failures does a provider-agnostic LLM client treat as transient and retry with real backoff — and how do you inject cross-provider prompt framing exactly once?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/llm_client/client.py:is_server_or_retry_error` (:62–72), `LLMClient.__init__` (:76–92, NoOpTracer default), `_clean_input` (:98–118), `_generate_response_with_retry` tenacity decorator (:120–130), `_apply_attribute_extraction_preamble` (:159–195), `generate_response` template (:197–267); `llm_client/errors.py` (`RateLimitError`, `RefusalError`, `EmptyResponseError`).
**Signature:** `generate_response(messages, response_model=None, max_tokens=None, model_size=ModelSize.medium, group_id=None, prompt_name=None, *, attribute_extraction=False) -> dict`.
**Data Shape:** subclasses implement ONLY `_generate_response`; the base owns cleaning, schema injection, language instruction, tracing span (`llm.generate`, attributes incl. optional `prompt.name`), cache lookup, and retry.

### Decisive source
```python
def is_server_or_retry_error(exception):
    # EmptyResponseError is treated as transient: an empty body is most often a
    # flaky provider/endpoint hiccup ... A persistent empty response still fails
    # after bounded retries.
    if isinstance(exception, RateLimitError | EmptyResponseError | json.decoder.JSONDecodeError):
        return True
    return (isinstance(exception, httpx.HTTPStatusError)
            and 500 <= exception.response.status_code < 600)

@retry(stop=stop_after_attempt(4),
       wait=wait_random_exponential(multiplier=10, min=5, max=120),
       retry=retry_if_exception(is_server_or_retry_error), reraise=True)
async def _generate_response_with_retry(self, messages, ...): ...

sentinel = '<<graphiti.attr_extraction.preamble.v1>>'   # idempotency marker
```

**Flow:** clean every message (utf-8 errors='ignore' round-trip → strip zero-width chars `\u200b\u200c\u200d\ufeff\u2060` → drop control chars except `\n\r\t`) → optionally append attribute-extraction preamble to messages[0] (system gets it appended; non-system gets it PREPENDED; sentinel short-circuit makes it idempotent across nested overrides; bump the version suffix when revising note text so old callers don't suppress the new copy) → append extraction-language instruction keyed off group_id → span-wrap → cache-check → retried call.
**Invariant:** (1) the transient set is EXPLICITLY {RateLimitError, EmptyResponseError, JSONDecodeError} ∪ {httpx 5xx} — 4xx other than 429-as-RateLimitError never retries; (2) backoff is randomized-exponential capped at 120s with reraise after 4 attempts; (3) preamble mutation must be idempotent WITHOUT coordinating with subclasses (concrete clients call it again); (4) `_get_failed_generation_log` truncates output at 500 chars and logs only roles/counts — PII discipline on failure paths.
**Probe:** `tests/llm_client/test_openai_generic_client.py:139 empty_response_error_is_retryable`; `:160 non_retryable_error_is_not_retried` (exactly one create call); `tests/llm_client/test_client.py:29 test_clean_input`, `:69 preamble_appends_to_system`, `:82 preamble_is_idempotent`, `:94 falls_back_to_first_message_if_no_system`, `:104 handles_empty_messages`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "is_server_or_retry_error _apply_attribute_extraction_preamble _clean_input retry", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit transient taxonomy + sentinel-idempotent preamble pattern verbatim; adapt attempt counts/backoff ceilings to host SLOs; omit the SQLite response cache if calls are cheap (see llm-cache-sqlite for when you need it). CORRECTS prior capsule revision which described retrying "server/rate-limit errors" only — EmptyResponseError/JSONDecodeError are first-class transients since the generic-client rework.
