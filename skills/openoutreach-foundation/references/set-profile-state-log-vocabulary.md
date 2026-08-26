<!-- capsule-v2 -->
# set_profile_state transition vocabulary — how does a state change stay legible in a log without a state-machine framework?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How should funnel-state writes emit operator-visible evidence without double-logging and without crashing on unmapped states?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/db/deals.py:_STATE_LOG_STYLE` (:14-21), `set_profile_state` (:53-93), `create_disqualified_deal` (:122-147).
**Signature:** `set_profile_state(campaign, profile_url: str, new_state: str, reason: str = "", outcome: str = "", log: bool = True)`; raises `ValueError` when no Deal exists.
**Data Shape:** `_STATE_LOG_STYLE: dict[DealState, (label, color, attrs)]` — every transitionable state needs an entry or the fallback renders a bold red `ERROR`.

### Decisive source
```python
deal.state = ps
if reason:  deal.reason = reason
if outcome: deal.outcome = outcome
deal.save()

label, color, attrs = _STATE_LOG_STYLE.get(ps, ("ERROR", "red", ["bold"]))
if not log:
    return
if state_changed:
    logger.info("%s %s%s", profile_url, colored(label, color, attrs=attrs), suffix)
else:
    logger.debug("%s %s (unchanged)%s", profile_url, label, suffix)
```

**Flow:** campaign-scoped lookup by `lead__profile_url` → missing deal raises loudly (`cannot set state`) → write + save → one spine line per *changed* state at INFO; an idempotent re-set degrades to DEBUG so repeated cycles don't spam. Callers that render their own aligned block pass `log=False` to avoid double emission.
**Invariant:** A benign enrichment miss must never look like a failure: `NO_EMAIL_BETTERCONTACT` logs as muted yellow `NO EMAIL`, red bold `FAILED` is reserved for genuine failures — this exact regression is test-locked. Disqualification from the LLM is created atomically as FAILED+WRONG_FIT **campaign-scoped**, never as `Lead.disqualified` (that column is the permanent account-level exclusion); the first shipped export filtered only the second and leaked rejections.
**Probe:** `tests/db/test_deals.py` (:33-49) — caplog asserts `"NO EMAIL" in line and "FAILED" not in line` for the miss, the reverse for a true failure.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "set_profile_state _STATE_LOG_STYLE deal transition", limit: 10 });
```

## Verdict
Adopt: one write-helper owning state mutation + its log spelling; changed-vs-unchanged log-level split; opt-out flag for callers with their own rendering; loud error on transitioning a nonexistent row; style-table fallback that fails visibly (`ERROR` label) instead of silently. Adapt colors/labels to your logger; omit termcolor.
