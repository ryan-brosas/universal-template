<!-- capsule-v2 -->
# Conversation-locked compatibility retries — which legacy retry path runs WITHOUT a policy, and how do provider-managed retries get disabled?

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e`; Codebase Memory project `openai-agents-python`. **Question:** How does the runner preserve the historical `conversation_locked` retry behavior while layering a policy engine on top, and when are hidden SDK retries turned off?

## Compatibility ladder + provider-disable matrix
**Path/Symbol:** `src/agents/run_internal/model_retry.py:` `COMPATIBILITY_CONVERSATION_LOCKED_RETRIES = 3` (:47), `_should_preserve_conversation_locked_compatibility` (:393–402), `_should_disable_provider_managed_retries` (:405–443), `_should_disable_websocket_pre_event_retry` (:446–460), loops in `get_response_with_retry` (:463–569) / `stream_response_with_retry` (:572–696).
**Signature:** `def _should_disable_provider_managed_retries(retry_settings, *, attempt, stateful_request, replay_unsafe_request) -> bool`.
**Data Shape:** two attempt counters (`request_attempt` vs `policy_attempt`), plus `failed_policy_attempts` and `compatibility_retries_taken` feeding `apply_retry_attempt_usage`.

### Decisive source
```python
if (
    not replay_unsafe_request
    and _is_conversation_locked_error(error)
    and _should_preserve_conversation_locked_compatibility(retry_settings)
):
    if compatibility_retries_taken < COMPATIBILITY_CONVERSATION_LOCKED_RETRIES:
        compatibility_retries_taken += 1
        delay = 1.0 * (2 ** (compatibility_retries_taken - 1))   # 1s, 2s, 4s
        await rewind()
        await _sleep_for_retry(delay)
        request_attempt += 1
        continue     # NOTE: policy_attempt NOT advanced — compat retries are invisible to policy
```
Disable matrix: replay-unsafe requests always disable provider retries; explicit `max_retries=0` disables them (full opt-out incl. hidden SDK retries); stateful requests disable them from attempt >1 (runner owns rewind decisions); stateless without policy keep provider retries forever; stateful with policy disable from attempt 1.

**Flow:** each loop iteration pulls the response/stream under contextmanagers that disable provider-managed + WS pre-event retries per the matrix → success folds ALL failed attempts into usage as zero-token entries PREPENDED to real entries → failure first checks the compat ladder (never counted against policy budget), then provider advice + policy evaluation. Stream variant tracks `emitted_retry_unsafe_event` once any event outside `{response.created, response.in_progress}` was YIELDED, closes the suspended generator explicitly, and publishes `failed_retry_attempts_out` alongside every yield so usage accounting survives terminal responses that omit usage.

**Invariant:** Compatibility retries must neither consume policy budget nor be double-counted by usage folding; provider-side hidden retries must never run when the runner itself is deciding replays of stateful requests.

**Probe:** `tests/test_agent_runner.py:3418–3425` builds the locked error fixtures; streamed twin `tests/test_agent_runner_streamed.py::_conversation_locked_error` (:79).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "conversation locked compatibility retry provider managed disabled", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt dual-counter separation whenever a legacy retry path coexists with a new policy engine; adapt error matching to your provider codes; omit the WS toggle if unused.
