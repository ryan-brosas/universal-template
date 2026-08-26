<!-- capsule-v2 -->
# Error-string classification — why classify from the flattened error STRING when exception objects are gone, and which class must win?

**Source:** pipeshub-ai Apache-2.0 @ `main` (pin `6850972`); Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** two surfaces (agent completed with success=False; stream_bridge top-level handler) see only `AgentResult.error: str` — how do both render the same errorCode vocabulary?

## Hint-ladder classifier with content_filter first
**Path/Symbol:** `backend/python/app/agents/agent_loop/error_classification.py:57-82` (`classify_error`); hint tables :29-40; shared by RespondPipeline._emit_error_response and stream_bridge.
**Signature:** `classify_error(error_msg: str) -> tuple[str, str]` returning `(error_code, user_message)` over exactly `content_filter | rate_limit | auth_error | server_error | timeout | unknown`.
**Data Shape:** lowercase substring matching against fixed hint tuples; user messages are static per class (never interpolate provider text).

### Decisive source
```python
# Provider content-moderation rejections ... Checked FIRST: these
# bodies routinely also contain words that match the broader hint
# lists below, and unlike every other class this one is
# deterministic — retrying the identical prompt always fails again,
# so telling the user "please try again" (the rate-limit/server-error
# advice) would be actively wrong.
if any(hint in lower for hint in _CONTENT_FILTER_HINTS):
    error_code = "content_filter"
elif any(hint in lower for hint in _RATE_LIMIT_HINTS):
    error_code = "rate_limit"
```

**Flow:** flatten → priority ladder content_filter → rate_limit → auth_error → server_error → timeout → unknown → return paired static user message.
**Invariant:** string-matching is DELIBERATE — `Agent.fail()` flattened the original exception away before these call sites. Content-filter MUST be checked before status-code hints because filter bodies routinely embed codes/words that would misclassify as retryable; rate_limit outranks server_error for the same reason (most actionable wins). User messages never leak raw provider text.

### Direct test
**Probe:** `tests/unit/agents/adapter/test_error_classification.py::test_content_filter_wins_over_status_code_hints` :47, `.test_classify_error_prioritizes_rate_limit_over_server_error_hints` :74, `.test_classify_error_user_message_never_leaks_raw_provider_text` :57. Execute: `/tmp/psh17venv/bin/python -m pytest tests/unit/agents/adapter/test_error_classification.py -q` (5 passed at pin).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "classify_error errorCode vocabulary content_filter rate_limit", limit: 3, fields: ["signature", "name", "file"] });
// resolves classify_error Function error_classification.py 57-82 rank#1 + its direct tests rank#2/#3
```

## Verdict
Adopt the priority-ordered hint ladder + static-message discipline for post-flattening error UX. Adapt hint vocabularies to your providers' error strings. Omit exception-type dispatch (unavailable at these call sites by design).
