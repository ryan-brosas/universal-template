<!-- capsule-v2 -->
# ACP stop-reason / usage plane — how does a turn's response encode which exit path fired?

**Source:** pydantic-ai-harness (MIT) `main@76db3dec`; Codebase Memory `pydantic-ai-harness`. **Question:** When mapping an agent run onto the Agent Client Protocol's `PromptResponse`, how do you fold finish reasons, usage-limit aborts, and late cancellations into `(stop_reason, usage)` without reporting uncommitted usage?

## Stop-reason folding over `_run_turn`'s four exit paths
**Path/Symbol:** `pydantic_ai_harness/experimental/acp/_adapter.py:_finish_reason_to_stop_reason` (:87–98), `_usage_limit_stop_reason` (:101–109), `_to_acp_usage` (:112–120), consumed by `_run_turn` (:594–686).
**Signature:** `_finish_reason_to_stop_reason(finish_reason: FinishReason | None) -> schema.StopReason`; `_usage_limit_stop_reason(exc: UsageLimitExceeded) -> schema.StopReason`; `_to_acp_usage(usage: RunUsage) -> schema.Usage`.
**Data Shape:** In: a completed run's terminal `finish_reason`, or a raised `UsageLimitExceeded` whose exception carries **no structured detail** (only its message text). Out: one of `end_turn | max_tokens | refusal | max_turn_requests | cancelled`, plus optional UNSTABLE `schema.Usage` fields.

### Decisive source
```python
def _finish_reason_to_stop_reason(finish_reason: FinishReason | None) -> schema.StopReason:
    if finish_reason == 'length':
        return 'max_tokens'
    if finish_reason == 'content_filter':
        return 'refusal'
    return 'end_turn'

def _usage_limit_stop_reason(exc: UsageLimitExceeded) -> schema.StopReason:
    # The exception carries no structured detail, so this reads its message; an
    # unrecognized wording falls back to `max_turn_requests`.
    return 'max_tokens' if 'tokens_limit' in str(exc) else 'max_turn_requests'
```

**Flow:** Completed turn → per-pause usage accumulation (`usage += result.usage` inside the resume loop, :634) → `_finish_reason_to_stop_reason(result.response.finish_reason)` → commit history/transcript → return `PromptResponse(stop_reason, usage=_to_acp_usage(usage))`. Usage-limit turn (:656–662) → fail outstanding tool calls → **roll back like a cancellation** but answer with the limit's stop reason and **no usage**: `return schema.PromptResponse(stop_reason=_usage_limit_stop_reason(exc))`. Cancel landing inside the post-commit store save (:676–685) → turn already committed → warn "durable state is now behind", override `stop_reason = 'cancelled'`, keep committed usage in the response.
**Invariant:** The response never reports usage that was not committed to session state: a limit-aborted turn answers a limit stop reason with `usage is None`; only a finished (or cancel-after-commit) turn carries summed multi-pass usage. Cancellation is handled by the caller (`_run_turn`'s except path) and never reaches `_finish_reason_to_stop_reason`.
**Probe:** `tests/experimental/acp/test_acp.py` `TestStopReason` (:599–678): parametrized finish-reason table incl. `None→end_turn`; real-run tests pin `response.stop_reason == 'max_turn_requests'` with `response.usage is None` and empty session history after a default request_limit trip.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "usage limit stop reason map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-way fold: distinct meanings only for `length`/`content_filter`/limit-abort; message-text sniffing of `'tokens_limit'` as the documented fallback when the exception type is detail-free; rollback-without-usage for limit turns; cancel-after-commit answering `cancelled` with committed signals. Adapt the exact ACP stop-reason enum names to your wire protocol. Omit pydantic-ai-specific `FinishReason`/`RunUsage` plumbing.
