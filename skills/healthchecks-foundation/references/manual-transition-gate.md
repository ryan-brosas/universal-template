<!-- capsule-v2 -->
# Manual transition gate — how do pause/resume record intent without paging anyone?

**Source:** healthchecks BSD-3-Clause `master@29b5ec251059034b79e0120e2ff0c3e35d7bd9f8`; Codebase Memory `healthchecks`. **Question:** When a user pauses or resumes a check through UI or API, what exactly must be written so sendalerts never notifies on it, downtime math stays whole, and a resumed check cannot masquerade as healthy?

## front pause/resume twins + api pause/resume twins
**Path/Symbol:** `hc/front/views.py:pause` (:822-845), `hc/front/views.py:resume` (:850-863), `hc/api/views.py:pause` (:547-568), `hc/api/models.py:Check.create_flip` (:651-671).
**Signature:** `pause(request, code: UUID) -> HttpResponse`; `resume(request, code: UUID) -> HttpResponse`; `create_flip(new_status: str, reason: str = "", mark_as_processed: bool = False) -> None`.
**Data Shape:** Both surfaces share one mutation recipe: `create_flip(..., mark_as_processed=True)` → mutate fields → `save(update_fields=whitelist)`. Front returns redirects/AJAX-200; API returns JSON with CORS `*`. Divergent error codes for resume-on-non-paused: front **400**, API **409 Conflict**.

### Decisive source
```python
# hc/front/views.py — pause is idempotent and SILENT
if check.status == "paused":
    return redirect("hc-details", code)      # early return: NO flip, NO save
check.create_flip("paused", mark_as_processed=True)
check.status = "paused"
check.last_start = None
check.alert_after = None                    # NB: last_ping deliberately KEPT
check.save(update_fields=("status", "last_start", "alert_after"))
check.project.update_next_nag_dates()       # nag bookkeeping done HERE, not by sendalerts

# hc/front/views.py — resume resets to "new", not "up"
if check.status != "paused":
    return HttpResponseBadRequest()
check.create_flip("new", mark_as_processed=True)
check.status = "new"; check.last_start = None; check.last_ping = None; check.alert_after = None
check.save(update_fields=("status", "last_start", "last_ping", "alert_after"))
```

**Flow:** Guard clause first (already-paused / not-paused exits happen BEFORE any write) → create the Flip pre-marked processed → mutate exactly three (pause) or four (resume) fields → whitelisted save → reconcile project nag dates. The API twins mirror this byte-for-byte except response shaping (`JsonResponse(check.to_dict(v=request.v))`, ownership via `check.project_id != request.project.id` → 403).
**Invariant:** `mark_as_processed=True` stamps `flip.processed = flip.created` at INSERT time, which is the wall that keeps user intent out of the notification pipeline (sendalerts claims only `processed=None`). Pause keeps `last_ping` so history/durations survive the pause; resume clears it because "new" means never-pinged semantics — the next real ping then produces a silenced new→up transition instead of paging (this is WHY select_channels suppresses new→up; see flip-outbox-fanout). Idempotent re-pause must not create a second flip or the downtime fold would double-count the paused span.
**Probe:** `hc/front/tests/test_pause.py::test_it_does_not_pause_an_already_paused_check` (:80-91, asserts `assertFalse(Flip.objects.exists())`), `::test_it_pauses` (:18-32, flip.processed True "so sendalerts ignores it"), `::test_it_clears_next_nag_date` (:69-78); `hc/api/tests/test_resume.py::test_it_works` (:22-40, status=="new", all three datetime fields None, processed flip), `::test_it_handles_not_paused_checks` (:42-50, 409); `hc/api/tests/test_pause.py::test_it_does_not_pause_already_paused_check` (:114-127).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "pause resume create_flip mark_as_processed update_next_nag_dates", limit: 10 });
```

## Verdict
Adopt the guard-first idempotence, pre-processed flips for user-driven transitions, field-reset asymmetry between pause (keep last_ping) and resume (clear to "new"), and post-write nag reconciliation. Adapt response shapes and error-code conventions (healthchecks itself diverges: 400 vs 409 for the same misuse). Omit the AJAX/XMLHttpRequest branch if your client always follows redirects.
