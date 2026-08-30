<!-- capsule-v2 -->
# Sliding-window rate limiter — dual request+token queues under one lock

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how does a batch pipeline throttle BOTH requests/min and tokens/min to an LLM without deadlocking threads?

## Connected graph-selected seam
**Path/Symbol:** `graphrag_llm/rate_limit/rate_limiter.py`: `RateLimiter` (ABC :12) — `acquire(token_count)` as a `@contextmanager`; `sliding_window_rate_limiter.py`: `SlidingWindowRateLimiter` (:16-143); `rate_limit_factory.py` (`register_rate_limiter` :27, `create_rate_limiter` :50).
**Signature:** `with limiter.acquire(token_count): ...` — blocks until the request fits both windows, then yields.
**Data Shape:** config `{period_in_seconds=60, requests_per_period?, tokens_per_period?}`; two parallel deques — `_rate_queue: deque[float]` (timestamps) + `_token_queue: deque[int]` (token counts) — plus `_stagger = period / rpp`.

### Decisive source
```ts
while True:
    with self._lock:
        # evict entries older than the period from BOTH windows together
        while rate_queue[0] < current_time - period: rate_queue.popleft(); token_queue.popleft()
        if rpp and len(rate_queue) >= rpp: continue          # window full -> retry
        if tpp and sum(token_queue) >= tpp: continue         # token budget spent -> retry
        # deliberate exception: a single request larger than tpm still passes
        if tpp and token_count <= tpp and sum(token_queue) + token_count > tpp: continue
        if stagger > 0 and (last_time and current_time - last_time < stagger):
            time.sleep(stagger - (current_time - last_time)) # even pacing
        rate_queue.append(current_time); token_queue.append(token_count)
        break
yield   # request runs inside the context
```

**Flow:** every LLM call wraps in `acquire(estimated_tokens)` → loop re-checks under the lock (dropping the lock between iterations lets other threads interleave) → when both windows admit the request it's recorded and the call proceeds → response tokens are accounted by the caller's next acquire.
**Invariant:** requests and tokens are limited independently but recorded atomically (one deque pair, one lock); TPM is a soft limit — a request bigger than the whole period budget is never starved (`token_count <= tpp` guard); optional stagger paces calls evenly instead of burst-then-wait.
**Probe:** `tests/` rate-limit tests (rpp enforced over sliding 60s; tpm enforced; oversized request passes; stagger spacing).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "SlidingWindowRateLimiter acquire token_count RateLimiter stagger", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dual-window context-manager limiter with the oversized-request escape hatch; adapt periods/limits to host quotas.
