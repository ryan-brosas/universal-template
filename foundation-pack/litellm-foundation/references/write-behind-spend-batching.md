<!-- capsule-v2 -->
# Write-behind spend batching base class — how do you keep per-request cache writes off Redis while staying multi-instance correct?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** the shared substrate every routing strategy inherits for in-memory-first writes with periodic Redis sync.

## write-behind-spend-batching
**Path/Symbol:** `litellm/router_strategy/base_routing_strategy.py:BaseRoutingStrategy` (`_increment_value_in_current_window` :63-85, `periodic_sync_in_memory_spend_with_redis` :87-104, `_push_in_memory_increments_to_redis` :106-151, `_sync_in_memory_spend_with_redis` :174-230).
**Signature:** `_increment_value_in_current_window(key: str, value: float, ttl: int) -> float`; subclass hook `get_key_pattern_to_sync() -> str | None`.
**Data Shape:** `redis_increment_operation_queue: list[RedisPipelineIncrementOperation]` (TypedDict `{key, increment_value, ttl}`); `in_memory_keys_to_update: set[str]` (docstring says max ~1000 keys).

### Decisive source
```python
# 4. Merge — redis wins unless in-memory is ahead; local-only deltas are preserved
redis_val = float(redis_values.get(key, 0) or 0)
before = float(in_memory_before_dict.get(key, 0) or 0)
after = float(await self.dual_cache.in_memory_cache.async_get_cache(key=key) or 0)
delta = after - before
if after <= redis_val:
    merged = redis_val + delta
else:
    continue
await self.dual_cache.in_memory_cache.async_set_cache(key=key, value=merged)
```
(:211-227)

**Flow:** every request-path increment lands ONLY in `in_memory_cache.async_increment` and appends a pipeline op to the queue → background task wakes every `DEFAULT_REDIS_SYNC_INTERVAL` → snapshot in-memory values BEFORE push (`in_memory_before_dict`) → compress queue by key (sum increments) → one `async_increment_pipeline` batch to Redis → re-read in-memory, compute local delta since snapshot, merge: if redis ≥ snapshot, memory = redis + delta; if redis < snapshot (another instance pushed more recently than our read? treat as ours ahead) skip. Loop never dies: exception logs and still sleeps the interval.
**Invariant:** the before-snapshot is what makes delta preservation possible — without it the merge would clobber concurrent local increments between push and read. Compression happens at PUSH time, not enqueue time, so per-request latency stays O(1). The sync task must be created FastAPI-compatibly (`setup_sync_task` falls back to `asyncio.new_event_loop()` when no running loop) and cancelled via `cleanup()` on shutdown.
**Probe:** `grep -cF 'redis_increment_operation_queue' litellm/router_strategy/base_routing_strategy.py` from repo root = **9**; direct tests: strategy-level suites GREEN this pass (test_budget_limiter_hotpath.py exercises the sibling implementation; least_busy/latency/cost suites GREEN 66 tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "periodic_sync_in_memory_spend_with_redis BaseRoutingStrategy", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the snapshot→compress→pipeline-push→delta-merge ladder wholesale — it is the reusable contract; adapt intervals/key patterns; omit the dead commented-out "shut down the proxy" debug block (:220-226) — it is vestigial.
