<!-- capsule-v2 -->
# Weighted shuffle + least-busy — how do the two "dumb" pickers behave at their edges?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** weighted-random selection semantics and in-flight traffic tracking without double-decrements.

## weighted-shuffle-least-busy
**Path/Symbol:** `litellm/router_strategy/simple_shuffle.py:simple_shuffle` (:21-72); `litellm/router_strategy/least_busy.py:LeastBusyLoggingHandler` (`log_pre_api_call` :24-48, `_get_available_deployments` :160-188).
**Signature:** `simple_shuffle(llm_router_instance, healthy_deployments: list, model: str) -> dict`; `async_get_available_deployments(model_group, healthy_deployments) -> dict`.
**Data Shape:** shuffle weights from FIRST deployment's `litellm_params.weight|rpm|tpm` presence; least-busy cache key `{model_group}_request_count` → `{deployment_id: int}`.

### Decisive source
```python
for weight_by in ["weight", "rpm", "tpm"]:
    weight = healthy_deployments[0].get("litellm_params").get(weight_by, None)
    if weight is not None:
        weights = [m["litellm_params"].get(weight_by, 0) for m in healthy_deployments]
        total_weight = sum(weights)
        if total_weight <= 0:
            # All remaining candidates have weight 0 for this metric (e.g.
            # after a weighted-failover exclusion left only zero-weight
            # backups). Skip to the next metric (rpm/tpm) which may still
            # provide a meaningful weighted pick; ...
            continue
        weights = [weight / total_weight for weight in weights]
        selected_index = random.choices(range(len(weights)), weights=weights)[0]
```
(simple_shuffle.py:43-59)

**Flow (least busy):** `log_pre_api_call` increments `{model_group}_request_count[id]` right before dispatch; success AND failure handlers decrement — None-aware (`if request_count_value is None: return` guards a decrement below an absent entry). Selection: min-traffic scan over ALL cached ids; unseen healthy deployments seeded to 0 so a fresh deployment wins immediately; if the min-id isn't found among healthy deployments (stale id / just-cooled deployment), fall back to uniform `random.choice`.
**Invariant:** (1) shuffle's trigger check reads ONLY deployment[0] but the weight VECTOR spans all deployments — mixed configs where the first deployment lacks `weight` silently degrade to uniform random; (2) zero-total weight for a metric skips to the next metric rather than raising, ending in uniform random as last resort; (3) least-busy decrements are best-effort inside bare excepts — the counter is advisory traffic shaping, not accounting; (4) both return the raw deployment dict (the `deployment or deployment[0]` tail handles the legacy list-shaped single deployment).
**Probe:** `tests/local_testing/test_least_busy_routing.py::test_get_available_deployments` (:40) GREEN at pin (unit slice); its Router e2e variants need OPENAI_API_KEY — blocked this window, recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "simple_shuffle weighted random deployment", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt zero-total skip-to-next-metric and seed-unseen-to-zero; adapt weight field names; omit the int→str id coercion only if your ids are already strings.
