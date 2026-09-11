<!-- capsule-v2 -->
# Spend gate & pool signature — one constant, one meaning; how do you stop a gate from becoming three?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you keep a confidence threshold from being reused for unrelated decisions, and how do you avoid refitting an expensive model when nothing changed?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/pipeline/ready_pool.py:promote_to_ready` (:39-91); `openoutreach/core/cycle.py:_score_qualified` (:216-242), `_pool_signature` (:245-258); `openoutreach/core/conf.py:CAMPAIGN_CONFIG["min_gp_confidence"]` (:73-85).
**Signature:** `promote_to_ready(campaign, qualifier) -> int`; `_pool_signature(campaign) -> tuple[int, int]`.
**Data Shape:** threshold = 0.75 (`min_gp_confidence`, P(f>0.5)); signature = `(deals awaiting the gate, deals already past it)`.

### Decisive source
```python
# ready_pool docstring: That constant is the **spend gate and nothing else**.
# Discovery once borrowed it to score query nodes ... calibrated against *labelled*
# leads the GP has memorized, the bar is unreachable for unlabelled candidates,
# so every node scored zero and discovery read a permanent wall.

threshold = CAMPAIGN_CONFIG["min_gp_confidence"]   # read HERE, not passed in,
                                                   # so it cannot drift from top_up's copy
...
if prob >= threshold:
    set_profile_state(campaign, p["profile_url"], DealState.READY_TO_FIND_EMAIL.value, log=False)

# cycle: skip scoring entirely while nothing moved
before = _pool_signature(campaign)
if before[0] == 0 or _scored_at.get(campaign.pk) == before:
    return False
promoted = promote_to_ready(campaign, qualifier_for(campaign))
_scored_at[campaign.pk] = _pool_signature(campaign)
```

**Flow:** QUALIFIED pool → predict_probs → ≥threshold ⇒ READY_TO_FIND_EMAIL (the only state the paid row will serve). Cycle-level memoization: re-scoring an unchanged pool cannot promote anybody, so the two-count signature gates the whole step ("measured ~1.1s at 300 labels against a 5s cycle").
**Invariant:** The second signature count stands in for the label set (every non-QUALIFIED state is a verdict; anchors thin out with acceptances), so any change to model inputs moves one of the two numbers; being wrong costs one cycle's delay, never a wrong answer. Process-local memo by design (one process per job). Promotion logs the posterior that justified it at DEBUG and never writes it into `reason` — that column holds the LLM's qualification rationale and overwriting it would destroy why the lead qualified. Exporting the GP score was tried and removed as a category error (see export capsule).
**Probe:** `tests/test_ready_pool.py::TestPromoteToReady` (:44-88), `tests/test_cycle.py::TestScoringIsSkippedWhenNothingMoved` (:269-315).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "promote_to_ready", limit: 5 });
```

## Verdict
Adopt single-meaning thresholds read from one shared constant at every use site; adopt cheap input-signature memoization ahead of expensive refits; adopt "score explains itself in logs, never mutates human-readable rationale columns". Adapt the gate value and state names; omit Django update_fields bookkeeping.
