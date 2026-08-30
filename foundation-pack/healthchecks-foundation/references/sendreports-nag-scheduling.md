<!-- capsule-v2 -->
# Nag scheduling — optimistic-lock due-date claiming for report/nag fan-out

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** Without a queue, how does the sendreports loop claim "profiles whose nag/report is due" across concurrent processes so each person gets exactly one email per period?

## sendreports Command: handle_one_report / handle_one_nag
**Path/Symbol:** `hc/api/management/commands/sendreports.py` (:18-133); Profile side `choose_next_report_date` (accounts/models.py :359-383), `update_next_nag_date` (:350-357), `send_report` (:208-291); daemon wiring `docker/uwsgi.ini:attach-daemon = ./manage.py sendreports --loop`.
**Signature:** `handle_one_report() -> bool`; `handle_one_nag() -> bool`; both True = "more work may exist".
**Data Shape:** Claim pattern: read profile → build queryset `filter(id=..., next_report_date=<read value>)` → conditional `update(next_report_date=...)` → proceed only if num_updated==1. Report window: 1st of month 09:00-11:00 local via `replace(hour=9) + randrange(120min)` then advance-day loop.

### Decisive source
```python
# hc/api/management/commands/sendreports.py — "a sort of optimistic lock"
qq = Profile.objects.filter(
    id=profile.id, next_report_date=profile.next_report_date
)
if profile.next_report_date is None:
    qq.update(next_report_date=profile.choose_next_report_date())
    return True
num_updated = qq.update(next_report_date=profile.choose_next_report_date())
if num_updated != 1:
    # next_report_date was already updated elsewhere, skipping
    return True

if profile.send_report():
    self.stdout.write(self.tmpl % profile.user.email)
    self.pause()      # throttle: avoid SMTP quota

# Nags degrade gracefully when nothing is down:
else:
    profile.next_nag_date = None     # no down checks → clear, retry next trigger
    profile.save()
```

**Flow:** handle(): SIGTERM/SIGINT cooperative shutdown flag; close_old_connections at top of loop; drain reports, drain nags; --loop sleeps in 60×1s slices checking shutdown. send_report refuses to mail accounts with no ping in 180 days (`test_send_report_noops_if_no_recent_pings`); nags filter to currently-down checks only.
**Invariant:** The WHERE clause carries the READ value of next_report_date/next_nag_date — that equality IS the lock; winner-takes-all and losers skip silently (num_updated!=1). Randomized 09-11h jitter spreads load instead of thundering-herding midnight; nags re-arm from `now + nag_period` only after a successful send and are CLEARED when no check is down so they don't spin. The pause() hook between sends is a rate-limit seam, mocked in tests (@patch time.sleep).
**Probe:** `hc/api/tests/test_sendreports.py::test_it_sends_monthly_report` (next date lands on Feb 1), `test_it_obeys_next_report_date`, `test_it_fills_blank_next_monthly_report_date`, `hc/accounts/tests/test_profile_model.py::test_send_report_noops_if_no_recent_pings`, `test_send_nag_noops_if_none_down`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "sendreports handle_one_report nag next_report_date", limit: 10 });
```
Resolves line-exact: Command methods :34-93.

## Verdict
Adopt value-equality optimistic claiming for time-due fan-out rows, jittered window computation by user tz, no-op-with-clear semantics for empty nags, and the 180-day liveness gate on reports. Adapt period vocabulary and mail throttling. Omit the UNION-vs-JOIN query tricks (Postgres-specific tuning) but keep their intent: profile enumeration must include owners AND members exactly once.
