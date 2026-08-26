<!-- capsule-v2 -->
# Alert-after partial-index scheduling — how does a poller find "about-to-die" checks in O(index) without scanning the table?

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** Why does every check write carry a denormalized `alert_after`, and why does the scheduler's claim update filter on the OLD status?

## Check.Meta partial index + sendalerts.handle_going_down
**Path/Symbol:** `hc/api/models.py:Check.Meta.indexes` (:227-237), `hc/api/management/commands/sendalerts.py:Command.handle_going_down` (:123-177).
**Signature:** `handle_going_down() -> bool` (True = caller should loop again immediately); model index `models.Index(fields=["alert_after"], name="api_check_aa_not_down", condition=~Q(status="down"))`.
**Data Shape:** Query: `Check.objects.filter(alert_after__lt=now()).exclude(status="down")` ordered by `alert_after` (deliberately NOT by id — avoids a second sort and lets the conditional index serve the query). The claim is `filter(id=check.id, status=old_status).update(alert_after=None, status="down")`.

### Decisive source
```python
# hc/api/management/commands/sendalerts.py — compute-then-claim
old_status = check.status
q = Check.objects.filter(id=check.id, status=old_status)   # optimistic lock on status

try:
    status = check.get_status()
except Exception:
    # Make sure we don't trip on this check again for an hour:
    # Otherwise sendalerts may end up in a crash loop.
    q.update(alert_after=now() + td(hours=1))
    raise

if status != "down":
    q.update(alert_after=check.going_down_after())   # not yet due: push deadline, retry later
    return True

flip_time = check.going_down_after()
assert flip_time   # get_status() just said down, so this must compute

num_updated = q.update(alert_after=None, status="down")
if num_updated != 1:
    # Nothing got updated: another worker process got there first.
    return True

flip = Flip(owner=check)
flip.created = flip_time      # backdated to when the flip REALLY happened
flip.old_status, flip.new_status, flip.reason = old_status, "down", "timeout"
flip.save()
```

**Flow:** Poller loop: while handle_going_down() returns True (work found) keep going; then drain process_one_flip; then sleep 2s. Per check: read candidate → compute true status OUTSIDE any transaction → if exception, defer one hour and re-raise (crash-loop guard) → if merely in grace, re-stamp alert_after → else CAS-flip status via `update() WHERE status=old` and create the Flip only when exactly 1 row updated.
**Invariant:** The condition index means "status=down rows" leave the scheduler's search space the moment they flip — but ONLY if alert_after is cleared to NULL on the same update; leaving a stale alert_after on a down check would still match nothing (index excludes down), yet corrupts to_dict/API output. Ownership is proven by `num_updated == 1` (compare postal's locked_by/locked_at stamp — same idea, single-column cheaper). Flip.created is backdated to grace_start+grace, not to processing time, so downtime statistics stay honest even under poller lag.
**Probe:** `hc/api/tests/test_sendalerts.py::test_it_creates_a_flip_when_check_goes_down` (asserts flip.created == check.alert_after, reason=="timeout", alert_after cleared), `test_it_does_not_clobber...` sibling `test_it_handles_grace_period` (Flip.objects.count()==0).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "sendalerts handle_going_down process_one_flip seats", limit: 10 });
```
Resolves line-exact: Command.handle_going_down :123-177.

## Verdict
Adopt the denormalized-deadline + condition-partial-index + compare-and-swap-status triple; it is what lets ONE polling process schedule millions of checks without locks or a broker. Adapt index DDL to your DB, the 1-hour crash-loop deferral constant, and backdating policy. Omit Django-specific Q objects if hand-writing SQL — but keep "clear the deadline when you consume it".
