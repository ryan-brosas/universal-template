<!-- capsule-v2 -->
# TieredCompaction escalation: anchored-baseline reclaim accounting + pin reinjection between tiers

## Source / Question
`pydantic_ai_harness/compaction/_tiered_compaction.py` — How do you run cheap-to-expensive compaction strategies in order and stop as soon as the history fits, when your token estimate is ANCHORED on provider-reported usage that predates every tier's rewrite? The naive loop re-anchors after each tier, sees "no reclaim", and always escalates to the most expensive tier.

## Path / Symbol
`compaction/_tiered_compaction.py` — `TieredCompaction` (32–127), `with_focus` (117–127 — a tiered strategy is focusable iff ANY tier is; the hint must REACH the summarizing tier), `_target` (129–139, realtime model → None guard), `_escalate` (141–167), `compact` (169–179), `before_model_request` (181–216).

## Signature
```python
baseline = estimate_context_tokens(messages, self.tokenizer, model_request_parameters=…)
heuristic_baseline = estimate_token_count(messages, self.tokenizer)
for tier in self.tiers:
    if estimate <= target: break
    messages = await tier.compact(messages, ctx)
    messages = reinject_pinned(original, messages)          # BEFORE next stop decision
    reclaimed = heuristic_baseline - estimate_token_count(messages, self.tokenizer)
    estimate = max(baseline - reclaimed, 0)
```

## Data Shape
`tiers: Sequence[CompactionStrategy]`, ordered cheap-to-expensive, last typically the summarizer. Target: exactly one of `target_tokens` / `target_fraction`; fraction resolved per-request against the model's window (`context_window` override applies even when registry resolution SUCCEEDS — for registries confidently wrong about beta/tier-gated or mislabeled self-hosted deployments; `fallback_context_window` only when unresolved). Each tier's own trigger is BYPASSED — the orchestrator drives `compact()` directly and owns the stop decision.

## Decisive source
The two-measurement accounting (:149–166): the usage anchor "describes the request as it was sent, so a tier's rewrite of older messages is invisible to re-anchoring" — you CANNOT re-anchor to measure a tier. Instead: subtract the tier-removed text estimated by the CHARACTER HEURISTIC from the anchored baseline. Two pinned consequences: (1) fixed overhead (tool definitions, instructions) inside the anchor is never treated as compacted away (:151–155); (2) "On content the estimator undercounts, this understates the reclaim and escalates a tier early -- the cheap direction" (:155). Gate resolves the target ONCE so gate and escalation loop cannot disagree (:192–193); tiers receive the REQUEST context (`context_for_request`) so a model-resolving tier reaches the same conclusion the gate did (:188–191).

## Flow / Invariant
Gate: if anchored estimate ≤ target → untouched. Else escalate: run tier → **reinject pins BEFORE the stop decision** ("escalation measures the history it would return", :163–164) → compute reclaim vs heuristic baseline → update anchored estimate → next tier only while estimate > target. Invariants: never trust post-rewrite re-anchoring; reclaim is measured on message TEXT only; pins survive every tier; single span wraps the whole escalation (`test_tiered_emits_single_span_not_one_per_tier` :2539).

## Probe (direct test)
`tests/compaction/test_compaction.py::TestTieredCompaction`: `test_short_circuit_first_tier_suffices` (:1866), `test_triggers_on_anchored_usage_the_heuristic_cannot_see` (:1882), `test_escalation_subtracts_tier_reclaim_from_anchored_baseline` (:1896), `test_escalation_never_counts_fixed_overhead_as_reclaimed` (:1917), `test_reinjects_pins_before_deciding_to_stop` (:1954), `test_composes_real_strategies` (:1965).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'TieredCompaction _escalate reinject_pinned'`

## Verdict
**Adopt** the anchored-baseline-minus-heuristic-reclaim ladder whenever a cheap estimate gates expensive remediation under a provider-reported anchor. **Adopt** bypass-tier-triggers + resolve-target-once so orchestrator and gate can't diverge. **Adapt** tier composition to your own strategy set.
