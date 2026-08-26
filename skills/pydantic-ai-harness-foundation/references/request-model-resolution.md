<!-- capsule-v2 -->
# Request-model resolution: context_for_request, trigger validation, realtime guard

## Source / Question
`pydantic_ai_harness/compaction/_shared.py` — Which model does a compaction/budget decision resolve against when a capability may SWAP the model between the run starting and the request leaving — and what happens on models with no window semantics at all? Porters read the run-start model and compact against the wrong window; or crash narrowing `Model` against a realtime session.

## Path / Symbol
`compaction/_shared.py` — `context_for_request(ctx, request_context)` (:380–396), `validate_token_trigger(max_tokens, max_fraction, fallback_context_window, context_window, *, tokens_name, fraction_name)` (:353–377), `resolve_token_trigger` (:410–450), `is_realtime_model` (:399–407), `compact_with_span` (:473–527), `_history_changed` (:462–470), `SupportsFocus` (:535–547).

## Signature
```python
def context_for_request(ctx: RunContext[D], request_context: ModelRequestContext) -> RunContext[D]:
    if request_context.model is ctx.model:
        return ctx                                  # common case: no swap
    return replace(ctx, model=request_context.model)

def resolve_token_trigger(max_tokens, max_fraction, model,
                          fallback_context_window=DEFAULT_CONTEXT_WINDOW,
                          context_window=None) -> int | None
```

## Data Shape
Triggers are mutually exclusive (`max_tokens` XOR `max_fraction`, 0 < f ≤ 1); fraction resolves to `max(1, int(window * max_fraction))`. Field names in errors are parameterized so TieredCompaction's `target_*` pair reports its own names.

### Decisive source
1. **Request model wins** (:380–396): "Everything a strategy reads off the context follows" the swapped model — the window a fraction resolves against and the model a summarizing tier calls; nested TieredCompaction included. Returns `ctx` itself (not a copy) when no swap.
2. **context_window override beats resolution** (:425–429): the registry "records the maximum a model can be made to accept — for a beta-gated or tier-gated window that is not what an ordinary request gets," and a self-hosted endpoint reports an id whose registry entry describes someone else's deployment; `fallback_*` can't cover those because it applies only when resolution FAILS.
3. **Realtime guard is type-soundness, not behavior** (:399–407, :435–443): "a realtime session never compacts — its history can't be modified mid-run"; the boolean check exists only because `RunContext.model` widened to `AbstractModel`; written as `isinstance(m, AbstractModel) and not isinstance(m, Model)` so callers keep the union without widening to `Model[Unknown]` (#585).
4. **No-op spans** (:496–503): receipts scope opens around `compact()`; unchanged histories emit NO span ("a no-op compaction emits nothing"); span name stays static `compact_messages` with strategy in an attribute to keep span cardinality low; `gen_ai.conversation.compacted` set true-only per GenAI semconv.

## Flow / Invariant
Capability hooks call `context_for_request` FIRST → validate trigger config → resolve absolute tokens (override > registry > fallback) → compare via anchored estimate. Invariants: one trigger source of truth; every downstream read (window, summarizer model) uses the SAME resolved model; non-instrumented runs pay zero overhead (tracer no-op + attributes computed only when recording).

## Probe (direct test)
`tests/compaction/test_context_budget.py`: `TestRequestModelIsTheOneResolved::test_sliding_window_trims_on_the_request_model` (:449), `test_a_nested_tiered_strategy_resolves_the_same_model` (:500), `test_a_summarizing_tier_calls_the_request_model` (:523); `TestTriggerValidation::test_reports_the_caller_field_names` (:260); `TestStrategyWindowOverride::test_the_override_beats_a_resolved_window` (:739), `test_the_override_is_ignored_without_a_fraction` (:761); `TestRealtimeModelSkipsTokenTriggers::test_a_realtime_model_resolves_to_no_trigger` (:1413); `TestCompactNowSpan::test_no_span_when_the_history_is_unchanged` (:1180).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'context_for_request resolve_token_trigger is_realtime_model compact_with_span'`

## Verdict
**Adopt** resolve-against-the-request-model for any per-request policy in a swappable-model runtime. **Adopt** explicit override > registry > conservative-fallback ladder. **Adapt** the fallback constant (here DEFAULT_CONTEXT_WINDOW) to your stack's floor.
