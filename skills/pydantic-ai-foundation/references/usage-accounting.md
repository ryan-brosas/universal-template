<!-- capsule-v2 -->
# Usage accounting — inclusive token buckets, unknown-cost semantics, and lossless round-trips

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How should a runtime model per-request and cumulative usage so limits, costs, and OTel export stay correct across providers?

## UsageBase / RequestUsage / RunUsage
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/usage.py:UsageBase` (:82-268), `RequestUsage.extract` (:303-334), `_incr_usage_tokens` (:398-414), `UsageLimits` (:417-574).
**Signature:** `RequestUsage.incr(other) -> None` (in-place); `__add__` returns `copy(self)` incremented; `UsageLimits.check_before_request(RunUsage)` / `.check_tokens(RunUsage)` / `.check_before_tool_call(projected_run_usage)` / `.check_per_request_input_tokens(int)`.
**Data Shape:** Token fields are INCLUSIVE buckets: `input_tokens ⊇ cache_write + cache_read + input_audio`, `cache_read ⊇ cache_audio_read`; `details: dict[str,int]` for provider extras; `cost: Decimal | None`. Legacy stored data deserializes via validation aliases (`request_tokens→input_tokens`, `response_tokens→output_tokens`) with `None→0` repair.

### Decisive source
```python
# usage.py:21-26 — the double-count guard for OTel emission
_FIRST_CLASS_TOKEN_DETAIL_KEYS = frozenset({'input_tokens', 'output_tokens'})
"""`details` keys whose names collide with the first-class `gen_ai.usage.{input,output}_tokens`
attributes. They must never be emitted under `gen_ai.usage.details.*` too: doing so reports the same
conceptual quantity under two attributes that consumers like Langfuse then sum, double-counting tokens
and cost."""

# usage.py:393-395 — cost is UNKNOWN-preserving, never zero-defaulting
def _incr_usage_cost(slf, incr_usage):
    if incr_usage.cost is not None:
        slf.cost = (slf.cost or 0) + incr_usage.cost

# usage.py:553-560 — projected check uses > (not >=): the call that lands exactly ON the limit is allowed
def check_before_tool_call(self, projected_usage: RunUsage) -> None:
    tool_calls_limit = self.tool_calls_limit
    tool_calls = projected_usage.tool_calls
    if tool_calls_limit is not None and tool_calls > tool_calls_limit:
        raise UsageLimitExceeded(...)
```

**Flow:** Each provider response → `RequestUsage.extract(data, provider=…, provider_url=…, provider_fallback=…)` tries genai-prices snapshot by URL → provider id → fallback id; all three failing yields a zero usage WITH details preserved (never an exception). Per request the executor adds to the run's cumulative `RunUsage`; numeric non-reserved fields sum generically (`__dict__` union minus requests/tool_calls/details/cost), details merge key-wise skipping non-numeric values. Limit checks run at three boundaries: BEFORE a request (request count ≥ limit blocks the NEXT one), AFTER each response (cumulative tokens/cost), and BEFORE dispatching tool calls against a PROJECTED count. `check_cost` warns (CostNotFoundWarning) when a limit was set but no price could be computed — silent enforcement gaps become visible.
**Invariant:** (1) Buckets stay inclusive everywhere — normalizing providers whose raw input_tokens exclude cache reads is REQUIRED before summation or cache-hit ratios lie. (2) Unknown cost propagates as `None`, distinguishable from genuine $0. (3) Arbitrary provider fields survive Pydantic round-trips via a custom core schema (reserved-name set = declared fields ∪ dir ∪ legacy keys; everything else re-set on validate and serialized back). (4) Request-count check is `>=` pre-request but tool-call projection is `>` post-projection — porters who unify these either block the first request or allow one call too many.
**Probe:** `tests/test_usage_limits.py::test_tool_call_limit` (:735 — exact boundary message `tool_calls=1` vs limit 0), `::test_output_tool_not_counted` (:793), `::test_usage_arbitrary_fields_pydantic_roundtrip` (:485), `::test_opentelemetry_attributes_excludes_first_class_token_details` (:377).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "UsageLimits check_before_tool_call RequestUsage extract incr", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt inclusive buckets, three-boundary limit checks with the >=/> asymmetry, and unknown-cost-as-None; adapt the genai-prices extraction ladder to your pricing source; omit the arbitrary-field core-schema trick only if your host never stores provider extras. Caveat: source read at HEAD this session.
