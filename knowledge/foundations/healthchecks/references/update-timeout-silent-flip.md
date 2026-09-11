<!-- capsule-v2 -->
# update_timeout silent-flip — schedule edits that would strand a check must create the processed Flip themselves

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** When a user shrinks a cron/simple schedule in the UI and the check is already past its new deadline, why must the view — not sendalerts — perform the down-transition, and what exactly does it write?

## views.update_timeout
**Path/Symbol:** `hc/front/views.py:update_timeout` (:604-666); contract twin `_update` in `hc/api/views.py` (:315-410, save(update_fields) discipline + Check.NotUpdated concurrent-delete handling per HEAD commit 29b5ec2).
**Signature:** `update_timeout(request, code: UUID) -> HttpResponse`; fields tuple `("kind", "timeout", "grace", "schedule", "tz", "alert_after")`.
**Data Shape:** Three form kinds (simple/cron/oncalendar) each validate fully before any field mutation; alert_after recomputed via going_down_after() BEFORE the up-check.

### Decisive source
```python
# hc/front/views.py — the comment IS the invariant
check.alert_after = check.going_down_after()
check_saved = False
if check.status == "up":
    assert check.alert_after
    if check.alert_after < now():
        # Checks can flip from "up" to "down" state as a result of changing check's
        # schedule.  We don't want to send notifications when changing schedule
        # interactively in the web UI. So we update the `alert_after` and `status`
        # fields, and create a Flip object here the same way as `sendalerts` would
        # do, but without sending an actual alert.
        #
        # We need to create the Flip object because otherwise the calculation
        # in Check.downtimes() will come out wrong (when this check later comes up,
        # we will have no record of when it went down).
        check.create_flip("down", mark_as_processed=True)
        check.alert_after = None
        check.status = "down"
        check.save(update_fields=fields + ("status",))
        check_saved = True
        check.project.update_next_nag_dates()   # nag bookkeeping normally owned by sendalerts

if not check_saved:
    check.save(update_fields=fields)
```

**Flow:** Validate form → assign kind-specific fields → recompute alert_after → if an "up" check's NEW deadline already passed: create Flip(down, mark_as_processed=True), clear alert_after, set status down, save with extended field tuple, refresh project nag dates; else plain save. Redirect preserves tags/search from Referer querystring.
**Invariant:** mark_as_processed=True is the load-bearing flag: the Flip exists ONLY so downtime statistics record the transition (sendalerts must never notify on it), which is exactly the inverse of the outbox capsule's unprocessed flips. The transition happens ONLY for status=="up" — a paused or new check edited this way stays untouched (test_it_does_not_update_status_to_up pins status=="down" survives). Every branch saves via update_fields whitelists, the same discipline that let API _update drop select_for_update entirely at HEAD (concurrent delete → Check.NotUpdated → 404).
**Probe:** `hc/front/tests/test_update_timeout.py::test_it_updates_status_to_down` (flip.processed True, next_nag_date set), `test_it_does_not_update_status_to_up`, `test_it_validates_cron_expression` (400 + original data intact), plus `hc/api/tests/test_update_check.py::test_it_handles_concurrent_delete`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "update timeout flip alert_after schedule", limit: 10 });
```
Resolves line-exact: test pins test_update_timeout.py :21-88.

## Verdict
Adopt "interactive edits pre-compute the deadline transition and write a self-processed flip" as a general rule for any scheduler with UI-editable schedules; keep update_fields whitelists and post-write nag reconciliation. Adapt form/kind structure freely. Omit nothing from the flag semantics — flipping mark_as_processed here silently pages people or corrupts downtime math elsewhere.
