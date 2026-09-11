<!-- capsule-v2 -->
# Best-effort pricing — cost must never fail a run, and expected vs unexpected failures differ

## Source / Question
`pydantic_ai_slim/pydantic_ai/_cost.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you attach a USD cost to every response when the pricing database is external, incomplete, and can reject inputs — without a pricing hiccup ever killing an agent run? A porter will let `LookupError` propagate or warn on every unknown model and flood users.

## Path / Symbol
`_cost.py` — `best_effort_price` (:62–95), `calculate_price_for_usage` (:29–59), `fill_response_cost` (:98–118), `preload_pricing_data` (:21–26).

## Signature
```python
def calculate_price_for_usage(usage, *, model_name: str,
    provider_api_url: str | None = None, provider_name: str | None = None,
    genai_request_timestamp: datetime | None = None) -> PriceCalculation: ...
def best_effort_price(usage, *, model_name: str | None, ...) -> PriceCalculation | None
def fill_response_cost(response: ModelResponse) -> None
def preload_pricing_data() -> None   # get_snapshot() at Model construction, off the event loop (#7405)
```

## Data Shape
Resolution ladder inside `calculate_price_for_usage`: try `provider_api_url` first (more specific); on `LookupError` fall through to `provider_name`. Only the public `ModelResponse.cost()` wants raising semantics; everything internal goes through `best_effort_price`, which degrades to `None`.

### Decisive source — the three-tier failure taxonomy (:78–95)
```python
if not model_name:
    return None                      # synthetic response: nothing to look up
try:
    return calculate_price_for_usage(...)
except (LookupError, ValueError):
    return None                      # EXPECTED: unknown model/provider, or usage that
                                     # implies negative uncached remainder — silent
except Exception as e:
    warnings.warn(f'Failed to get cost: {type(e).__name__}: {e}',
                  CostCalculationFailedWarning, stacklevel=2)
    return None                      # UNEXPECTED: surface as warning, still never raise
```
`fill_response_cost` writes only when `response.usage.cost is None` — an already-set cost is never overwritten (provider-reported costs take precedence) and missing pricing data stays `None`, distinguishing "unknown" from genuine zero.

**Flow:** run appends response → `fill_response_cost` → best-effort price → cost lands on `usage.cost`; run-level accumulation sums costs in `RunUsage.incr` with a guard against double-adding numeric costs.

**Invariant:** Pricing failures are data, not errors: expected misses are silent `None`s, only *unexpected* exception types escalate to a warning; a set cost is immutable.

**Probe:** `tests/test_usage_limits.py::test_calculate_price_for_usage_api_url_falls_back_to_provider_name` (:1266), `test_best_effort_price_unpriceable_usage_returns_none` (:1300 — drives real `calc_price` with cache_read_tokens > input_tokens), `test_best_effort_price_unexpected_error_warns` (:1312); `tests/test_cost.py::test_cost_is_silent_for_unpriceable_model` (:122), `test_cost_unexpected_failure_warns` (:155), `test_model_response_cost_requires_model_name` (:196).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'best_effort_price calculate_price_for_usage CostCalculationFailedWarning'
```

## Verdict
**Adopt** the whole contract: URL→name resolution fallback, no-name→None fast path, two-tier exception handling, set-cost immutability, and construction-time snapshot preload. **Adapt** the pricing backend and warning category names. **Omit** genai-prices specifics beyond the LookupError/ValueError shape.
