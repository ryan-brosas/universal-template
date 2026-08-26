<!-- capsule-v2 -->
# Router budget limiter — how do you enforce $ budgets per provider/deployment/tag as a FILTER that composes with any pick strategy?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** spend-based deployment filtering with sliding budget windows, sub-100ms hot path, and multi-instance consistency.

## router-budget-filter
**Path/Symbol:** `litellm/router_strategy/budget_limiter.py:RouterBudgetLimiting` (`async_filter_deployments` :115-189, `_filter_out_deployments_above_budget` :191-273, `_increment_spend_for_key` :455-502, `_push_in_memory_increments_to_redis` :522-548, `_get_llm_provider_for_deployment` :623-644).
**Signature:** `async_filter_deployments(model: str, healthy_deployments: list, messages, request_kwargs, parent_otel_span) -> list[dict]` — FILTER contract (narrows the candidate list; raises `ValueError(RouterErrors.no_deployments_with_provider_budget_routing)` only when everything is filtered out), NOT a picker.
**Data Shape:** cache keys `provider_spend:{provider}:{budget_duration}`, `deployment_spend:{model_id}:{duration}`, `tag_spend:{tag}:{duration}` + window anchors `provider_budget_start_time:{provider}` etc. Config = `{budget_limit: float, time_period: "1d"|"7d"|...}` parsed via `duration_in_seconds`.

### Decisive source
```python
# within existing window — increment in memory instantly, queue Redis write
remaining_time: Final = ttl_seconds - (current_time - budget_start)
ttl_for_increment: Final = int(remaining_time)
await self._increment_spend_in_current_window(
    spend_key=spend_key, response_cost=response_cost, ttl=ttl_for_increment
)
```
(:493-500) with `_increment_spend_in_memory_and_queue_redis` doing:
```python
await self.dual_cache.in_memory_cache.async_increment(key=spend_key, value=response_cost, ttl=ttl)
self.redis_increment_operation_queue.append(increment_op)
```
(:386-396)

**Flow:** filter phase: resolve provider per deployment ONCE (`_get_llm_provider_for_deployment`, loop-invariant tags resolved before the loop) → build ALL cache keys → ONE `async_batch_get_cache` for every spend (single round-trip) → three-stage per-deployment check (provider → deployment-by-model_id → any request tag), each stage can only mark not-within-budget → empty result raises the structured no-deployments error. Record phase (`async_log_success_event`): skip websocket wrapper call_types (`_aresponses_websocket`/`_arealtime` fire with result=None; inner calls carry cost), read `response_cost` from standard_logging_object, then increment each configured dimension's spend key. Window lifecycle: first-ever spend or expired `(now - start) > ttl` ⇒ `_handle_new_budget_window` RESETS spend key to this response's cost AND re-anchors start time; else increment with ttl = remaining window time so keys expire exactly when the window does.
**Invariant:** (1) it's a filter like tag-routing — compose with weighted-pick/lowest-latency/simple-shuffle, never replace them; (2) hot path writes go to in-memory FIRST (sub-100ms reads) with Redis sync pushed to a 1-second periodic task (`DEFAULT_REDIS_SYNC_INTERVAL=1`) — but unlike `BaseRoutingStrategy`, RouterBudgetLimiting pushes its whole queue via `asyncio.create_task(...)` WITHOUT compressing same-key increments and clears the queue unconditionally (fire-and-forget); (3) provider resolution uses a `_LiteLLMParamsDictView.__slots__` duck-typed view to feed `litellm.get_llm_provider` without pydantic construction in the request path; (4) tag budgets raise at INIT time if not premium (`_init_tag_budgets` imports proxy_server.premium_user and ValueError-fails) — enterprise gate lives in init, not in the filter; (5) runtime-added deployments register budgets via `register_deployment_budget`.
**Probe:** `tests/local_testing/test_router_budget_limiter.py::test_handle_new_budget_window` (:236), `test_get_or_set_budget_start_time` (:276), `test_increment_spend_in_current_window` (:316) GREEN at pin; plus `tests/test_litellm/router_strategy/test_budget_limiter_hotpath.py` 7 tests GREEN (dict-view mapping semantics, provider resolved once per filter). REDIS-hosted e2e slice of test_router_budget_limiter.py BLOCKED this window (needs live Redis service; recorded honestly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "RouterBudgetLimiting async_filter_deployments", limit: 5, fields: ["signature", "name", "file"] });
```
(rank-1 = budget_limiter.py:115-189.)

## Verdict
Adopt the filter-not-picker contract, single batched read, and reset-window-on-expiry choreography; adapt the write-behind queue to your infra (prefer BaseRoutingStrategy's compressed push if correctness-under-loss matters more than simplicity); omit the premium gate if your product has no tiering.
