<!-- capsule-v2 -->
# Lowest-latency routing — how do you pick the fastest deployment with per-token normalization, TTFT for streams, and a buffer band?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** latency-history recording and selection semantics including timeout penalties and stream/non-stream split.

## lowest-latency-scoring
**Path/Symbol:** `litellm/router_strategy/lowest_latency.py:LowestLatencyLoggingHandler` (`log_success_event` :37-164, `async_log_failure_event` :166-221, `_get_available_deployments` :356-491).
**Signature:** `async_get_available_deployments(model_group, healthy_deployments, messages, input, request_kwargs) -> dict | None`.
**Data Shape:** single cache key `{model_group}_map` → `{deployment_id: {"latency": [floats], "time_to_first_token": [floats], "{YYYY-mm-dd-HH-MM}": {"tpm": int, "rpm": int}}}`; `RoutingArgs`: ttl 1h, `lowest_latency_buffer=0`, `max_latency_list_size=10` (sliding window via `[1:] + [new]`).

### Decisive source
```python
# get average latency or average ttft (depending on streaming/non-streaming)
use_ttft = (
    request_kwargs is not None
    and request_kwargs.get("stream", None) is not None
    and request_kwargs["stream"] is True
    and len(item_ttft_latency) > 0
)
...
# Sort potential deployments by latency
sorted_deployments: Final = sorted(potential_deployments, key=lambda x: x[1])
lowest_latency = sorted_deployments[0][1]
buffer: Final = self.routing_args.lowest_latency_buffer * lowest_latency
valid_deployments: Final = [x for x in sorted_deployments if x[1] <= lowest_latency + buffer]
random_valid_deployment: Final = random.choice(valid_deployments)
```
(:435-486)

**Flow:** success handler: normalize timedelta→seconds FIRST (issue #33169 — non-ModelResponse branches would otherwise append raw timedelta breaking Redis JSON serialization), TTFT only when `kwargs["stream"] is True` (`completion_start_time - start_time`), normalize BOTH by completion_tokens (`safe_divide_seconds`) so long generations aren't penalized, append to ≤10-slot sliding lists, bump minute-keyed tpm/rpm. Selection: unseen deployments seeded `{"latency":[0], ...}`; TPM/RPM admission filter (`item_tpm + input_tokens > limit or item_rpm + 1 > limit → skip`) with limits read top-level→litellm_params→model_info→inf; random.sample shuffles iteration order so all-zero histories don't deterministically favor insertion order; average over floats only (non-float entries skipped); sort ascending; keep everything within `buffer × best`; uniform-random among the band.
**Invariant:** (1) failure handler records a 1000.0s penalty ONLY for `litellm.Timeout` — other failures leave history untouched; (2) TTFT list is consulted ONLY if the current request streams AND that deployment has TTFT samples — otherwise falls back to total-latency averages (mixed populations compare per-request-mode); (3) `_latency_per_deployment` debug map is written into request metadata for observability but is explicitly NOT used for routing (:455 comment); (4) `_select_metadata_field(kwargs)` mirrors budget_limiter's metadata/litellm_metadata duality.
**Probe:** `tests/local_testing/test_lowest_latency_routing.py` — `test_get_available_endpoints_tpm_rpm_check` (:339), `test_lowest_latency_routing_with_timeouts` (:571), `test_latency_memory_leak` (:30); suite GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "LowestLatencyLoggingHandler _get_available_deployments", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt per-token normalization + sliding-window cap + buffer-band tie-breaking; adapt the timeout-penalty constant to your SLOs; omit the debug map plumbing if you have no tracing surface.
