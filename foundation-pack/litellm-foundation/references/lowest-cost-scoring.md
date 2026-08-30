<!-- capsule-v2 -->
# Lowest-cost routing — how does "cheapest deployment" actually score, given the handler never records cost history?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** what lowest_cost really optimizes and which dead code a porter must not "fix" into behavior.

## lowest-cost-scoring
**Path/Symbol:** `litellm/router_strategy/lowest_cost.py:LowestCostLoggingHandler` (`async_get_available_deployments` :177-305; success handlers :21-175).
**Signature:** `async_get_available_deployments(model_group, healthy_deployments, messages, input, request_kwargs) -> dict | None`.
**Data Shape:** cache key `{model_group}_map` holds ONLY minute-keyed `{tpm, rpm}` counters (same shape as other strategies); per-deployment price from `litellm.model_cost[name]["input_cost_per_token"/"output_cost_per_token"]` or `litellm_params.input_cost_per_token/output_cost_per_token` overrides.

### Decisive source
```python
if item_input_cost is None:
    item_input_cost = item_litellm_model_cost_map.get("input_cost_per_token", 5.0)
if item_output_cost is None:
    item_output_cost = item_litellm_model_cost_map.get("output_cost_per_token", 5.0)

# if litellm["model"] is not in model_cost map -> use item_cost = $10
item_cost = item_input_cost + item_output_cost
...
potential_deployments.append((_deployment, item_cost))
...
potential_deployments = sorted(potential_deployments, key=lambda x: x[1])
selected_deployment: Final = potential_deployments[0][0]
```
(:259-305 — despite docstrings claiming `{id: {"cost": [...]}}` history at :122, no cost list is ever written.)

**Flow:** success handlers maintain minute tpm/rpm counters only (the `float(response_ms.total_seconds() / completion_tokens)` expressions at :64/:144 are computed-and-DISCARDED dead code copied from the latency strategy). Selection: admission-filter by tpm/rpm exactly like lowest-latency → static per-deployment price = input+output token costs (defaults 5.0 each when unknown) → strict sort ascending → pick index [0]. No randomness: exact ties go to the first in dict order.
**Invariant:** (1) this is STATIC price routing — traffic load never changes the pick except through the tpm/rpm admission filter; (2) unknown-model fallback is 5.0+5.0=10.0 per-token-pair, i.e. unknown models are treated as expensive, not free; (3) the `{"cost": [...]}` shape in docstring comments is aspirational copy — do not implement consumers against it without adding the recording yourself.
**Probe:** `tests/local_testing/test_lowest_cost_routing.py::test_get_available_deployments_custom_price` (:50) GREEN at pin (custom litellm_params pricing path); `grep -c 'item_cost = item_input_cost + item_output_cost' litellm/router_strategy/lowest_cost.py` = **1**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "LowestCostLoggingHandler async_get_available_deployments", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the price-key ladder with explicit unknown-model default; adapt defaults to your catalog; omit nothing silently — if you want true marginal-cost routing you must ADD cost-history recording (the upstream module deliberately ships without it).
