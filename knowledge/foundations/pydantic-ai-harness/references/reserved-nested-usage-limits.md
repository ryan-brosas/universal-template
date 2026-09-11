<!-- capsule-v2 -->
# Reserved usage limits: nested summarizer runs must not spend the parent's approved request

## Source / Question
`pydantic_ai_harness/_usage.py` (18L whole file) @ `main@f971198` — A nested agent call fired from a hook/capability (summarize-this-output) may run AFTER the parent request already passed its limit check; how do you stop the child from consuming the request budget that was approved for the parent, without corrupting any other limit field?

## Path / Symbol
`_usage.py` — `reserved_usage_limits(limits)` (:10–18); consumers: `compaction/_summarizing_compaction.py:641`, `tool_output_limits/_capability.py:461`, `system_reminders/_capability.py:296` — all three pass `usage=ctx.usage, usage_limits=reserved_usage_limits(ctx.usage_limits)`.

## Signature
```python
def reserved_usage_limits(limits: UsageLimits | None) -> UsageLimits | None:
    if limits is None or limits.request_limit is None:
        return limits                       # SAME OBJECT returned, not a copy
    return replace(limits, request_limit=max(0, limits.request_limit - 1))
```

## Data Shape
Only `request_limit` moves, and only when finite; every other field (cost, token counts, `count_tokens_before_request`) passes through untouched via `dataclasses.replace`. Zero clamps at `max(0, ...)` so an already-exhausted limit stays valid rather than going negative.

### Decisive source
Docstring invariant (:11–14): "The hook may run after the parent request's limit check. Reducing a finite request limit prevents the nested call from spending the request that was already approved for the parent." Absent/unbounded limits are returned IDENTITY-preserved — tests pin `is limits`, so porters must not "helpfully" deep-copy.

**Flow:** capability holds parent ctx → fires nested `agent.run(..., usage=ctx.usage, usage_limits=reserved_usage_limits(ctx.usage_limits))` → child sees one fewer allowed request → child usage still folds into shared `ctx.usage`.
**Invariant:** never mutate the caller's `UsageLimits`; identity-return for None/unbounded; clamp at zero.

## Probe (direct test)
`tests/test_usage.py` — `test_reserved_usage_limits_reserves_one_request_and_preserves_other_limits` (:14, full 8-field UsageLimits ⇒ only request_limit 1→0), `test_reserved_usage_limits_clamps_zero_request_limit` (:29), `parametrize [None, UsageLimits(request_limit=None)] … assert reserved_usage_limits(limits) is limits` (:35–37).

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'reserved_usage_limits' --detail ids
```

## Verdict
**Adopt** whenever a library fires hidden nested model calls inside a user-visible run. **Adapt** which limit to reserve if your provider counts differently. **Omit** nothing else.
