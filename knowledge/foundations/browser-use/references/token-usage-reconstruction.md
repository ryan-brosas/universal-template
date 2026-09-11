<!-- capsule-v2 -->
# Token usage reconstruction — how do you rebuild a usage/cost summary from per-turn usage events with two competing vocabularies?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how do you fold `model.usage` (per-call deltas) and `token_count` (cumulative snapshots) events into one `UsageSummary`, and price it, without double-counting cache reads?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/beta/service.py` — bucket normalization `_input_usage_buckets` (:3029) + `_cache_creation_usage_tokens` (:3016), completion `_usage_completion_tokens` (:3068, adds reasoning tokens), total `_usage_total_tokens` (:3072); folding `_usage_from_events` (:3084); pricing `_usage_from_events_with_costs` (:3197) via `TokenCost.calculate_cost`; response-side override `_usage_event_from_sdk_history_usage` (:3181) + `_usage_tokens` (:3170).
**Signature:** `_input_usage_buckets(usage: dict) -> tuple[int,int,int,int,int]` = (input, cache_read, cache_creation, cc_5m, cc_1h); `_chat_invoke_usage_from_payload(usage) -> ChatInvokeUsage | None` (:3038).
**Data Shape:** `model.usage` payload → `usage` dict (or the payload itself); `token_count` payload → `info.total_token_usage` / `info.last_token_usage`. Cache-read aliases: `cache_read_input_tokens|input_cached_tokens|cached_input_tokens`; cache-write aliases incl. Anthropic-style nested `{ephemeral_5m_input_tokens, ephemeral_1h_input_tokens}`.

### Decisive source
```python
input_tokens = _int_value(usage.get('input_tokens'))
if 'cache_read_input_tokens' in usage or 'cache_creation_input_tokens' in usage:
    input_tokens += cache_read_tokens      # Anthropic dialect reports EXTERNAL cache reads
# completion includes reasoning tokens:
return _int_value(usage.get('output_tokens')) + reasoning_output_tokens
# total: computed wins over reported whenever the cache-keyed dialect is present;
# otherwise trust provider total only when positive or computed is zero
# THE FOLD:
if event_type == 'model.usage':
    input += ...; completion += ...        # SUM every event
elif event_type == 'token_count':
    ...
    input = max(input, total_from_snapshot, running_token_count_sums)   # MAX, never +=
```

**Flow:** sum all `model.usage` deltas; for `token_count` snapshots take max of (current totals, snapshot totals, running sums of last_usage); invocation count is `max(model_usage_events, token_count_events)`; pricing pass re-walks events, SKIPS `token_count` entirely when any `model.usage` exists (`has_model_usage` guard :3218-3220) so cumulative snapshots can't double-count per-call deltas, prices each call via TokenCost and rewrites cost fields only for priced invocations; if the SDK response carries its own `history.usage`, it becomes the sole usage event when its token count exceeds the event-derived one.
**Invariant:** the two vocabularies use opposite folds (sum vs max) — mixing them double-counts; cache reads are added into prompt tokens ONLY under the explicit Anthropic key dialect (presence-of-key test, not truthiness); a zero-token usage payload returns None so empty runs stay unpriced; costs are additive across priced calls and replace (not merge with) reconstructed estimates.
**Probe:** `tests/ci/test_beta_agent.py:1978` `test_rust_terminal_usage_prices_anthropic_raw_cache_reads`, `:2257` `test_rust_terminal_priced_usage_prefers_model_usage_over_token_count`, `:2316` `test_rust_token_summary_does_not_double_count_cache_reads`, `:2104` `test_rust_terminal_usage_priced_summary_sums_cache_read_tokens`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "_usage_from_events_with_costs _input_usage_buckets token_count model.usage", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the sum-vs-max dual fold + has_model_usage pricing guard + presence-keyed cache-read promotion exactly — these encode upstream billing semantics; adapt alias key lists to your providers; omit the 5m/1h ephemeral split if your models have no tiered cache pricing.
