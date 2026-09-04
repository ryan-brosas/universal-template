<!-- capsule-v2 -->
# Job goal-bounded run — how does a batch loop stop honestly and count what it produced?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you bound a work loop by a goal ("10 more leads") when the loop's steps can produce, un-produce, and pay for things asynchronously — without a timeout?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/job.py:_work_to_goal` (:101-148), `_unit_ids` (:153-168), `_presented_ids` (:171-189), `_lookup_budget` (:192-201), `_collect` (:204-217).
**Signature:** `_work_to_goal(campaign, goal: Goal, on_new_lead, buy_addresses: bool, started: float) -> JobResult`.
**Data Shape:** `Goal(count: int, unit: "leads"|"emails")` — count is a **delta**, not a total. `JobResult{goal, produced_ids: list[int], stopped_because: str|None, detail, elapsed}`; `stopped_because is None` ⇔ goal met. Every exit is a JobResult; none raises.

### Decisive source
```python
baseline = _unit_ids(campaign, goal.unit)
presented_baseline = _presented_ids(campaign) if goal.unit == EMAILS else None
while result.produced < goal.count:
    acted = run_one_action(campaign, buy_addresses=buy_addresses,
                           max_new_lookups=_lookup_budget(campaign, goal, presented_baseline))
    _collect(campaign, goal, baseline, result, on_new_lead, started)
    ...
    if not acted and result.produced < goal.count:
        result.stopped_because = ErrorType.GOAL_UNREACHED
        result.detail = _why_idle(campaign, result, buy_addresses)   # names the holding gate
        return result

def _lookup_budget(campaign, goal, presented_baseline):
    if presented_baseline is None:
        return None
    new_presented = len(_presented_ids(campaign) - presented_baseline)
    return max(0, goal.count - new_presented)
```

**Flow:** snapshot baseline sets → loop {one action → collect fresh entries} → halting errors (ModelHTTPError→BAD_CONFIG) / provider refusals (BetterContactUnavailable carries its own error_type) / KeyboardInterrupt all return a populated JobResult with the rows already produced → `not acted` with an unmet goal stops with GOAL_UNREACHED + why-idle line.
**Invariant:** **Progress is a set, not a subtraction**: `fresh = _unit_ids(...) − baseline − produced_ids`, so a lead rejected mid-run can never cancel one that entered. For `emails` goals the cap is on *newly presented* deals (`FINDING_EMAIL ∪ RESOLVED ∪ NO_EMAIL_BETTERCONTACT` minus baseline), because a submission almost never resolves synchronously — capping on `produced` alone would let "1 email" submit paid lookups for every lead past the gate. Unit ≠ permission: `buy_addresses` is separately required even for an emails goal.
**Probe:** `tests/test_job.py::TestEmailsGoalCapsNewSubmissions` (:130-178), `TestReachingTheGoal` (:42), `TestStoppingShort::test_a_halting_error_stops_with_its_own_name`-class coverage in :179+, `TestUnits` (:92).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "_lookup_budget", limit: 5 });
```

## Verdict
Adopt baseline-set-delta accounting, the presented-set budget for async-paid units, typed stop reasons instead of exceptions across the loop boundary, and "no timeout" (each unit of work already carries its own wait via per-row `not_before`). Adapt unit definitions to your export shape; omit Django-specific id plumbing and the termcolor progress narration.
