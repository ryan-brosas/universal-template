<!-- capsule-v2 -->
# Ping ingest transaction — why must a heartbeat update and its audit row commit atomically?

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks` (re-pinned pass 2 from retired `ext-healthchecks`, same HEAD). **Question:** How does one inbound ping correctly interleave check-state mutation, run-ID bookkeeping, and the append-only ping log without races or deadlocks?

## Check.ping + views.ping
**Path/Symbol:** `hc/api/models.py:Check.ping` (:492-572), `hc/api/views.py:ping` (:179-244), `hc/api/urls.py:uuid_urls` (:44-50).
**Signature:** `ping(remote_addr: str, scheme: str, method: str, ua: str, body: bytes, action: str, rid: uuid.UUID | None, exitstatus: int | None = None) -> None`.
**Data Shape:** `action ∈ {success, start, fail, log, ign}`; check fields touched: `last_start`, `last_start_rid`, `last_ping`, `last_duration`, `status`, `alert_after`, `n_pings` (via `F("n_pings") + 1`), `has_confirmation_link`. Side outputs: a Ping row and (rare) a Flip row; body goes to S3 when `len(body) > 100 and settings.S3_BUCKET`.

### Decisive source
```python
# hc/api/models.py — the whole ingest is ONE transaction
with transaction.atomic():
    # Acquire a lock. Without locking, on MariaDB, concurrent pings can
    # lead to a deadlock
    self = Check.objects.select_for_update().get(id=self.id)
    ...
    elif action in ("success", "fail"):
        self.last_ping = frozen_now
        self.last_duration = None
        if self.last_start:
            if self.last_start_rid == rid:
                # rid matches: calculate last_duration, clear last_start
                self.last_duration = self.last_ping - self.last_start
                self.last_start = None
            elif action == "fail" or rid is None:
                # clear last_start on: success with no rid / any fail
                self.last_start = None

    new_status = "down" if action == "fail" else "up"
    if self.status != new_status:
        reason = "fail" if action == "fail" else ""
        self.create_flip(new_status, reason=reason)
        self.status = new_status

    self.alert_after = self.going_down_after()
    self.n_pings = models.F("n_pings") + 1
    ...
    self.save()
    ping = Ping(owner=self); ping.n = self.n_pings; ... ping.save()

# OUTSIDE the transaction:
if ping.object_size:
    put_object(self.code, ping.n, body)          # S3 can be slow — don't hold the row lock
if self.n_pings % 100 == 0:
    self.prune()                                  # amortized GC every 100 pings
```

**Flow:** HTTP view resolves the check (by UUID or slug), normalizes client IP from X-Forwarded-For (first hop; strips Azure-style ipv4:port; passes IPv4-mapped IPv6 through verbatim), classifies the action, then calls ping() which does everything inside one select_for_update transaction.
**Action precedence (sharpened pass 2 against :200-222 + tests):** (1) `exitstatus > 255` ⇒ 400 "invalid url format" BEFORE anything runs; (2) `exitstatus > 0` ⇒ action="fail"; (3) `check.methods == "POST"` with a non-POST request ⇒ action="ign" — this OVERRIDES step 2, so a POST-only check receiving `GET /fail` records an ign and its state is untouched; (4) body-keyword filtering (`failure_kw → success_kw → start_kw → filter_default_fail → ign`) runs ONLY when `action != "ign"`; (5) `rid` query param must parse as a UUID string else 400. Pinned by `test_it_requires_post` (:306-319, kind=="ign", check stays "new") and `test_it_rejects_exit_status_over_255` (:377-379).
**Invariant:** State change + audit log commit together because sendalerts may observe the updated Check before the Ping exists otherwise (upstream's own comment names the race). The rid-matching table is the porter trap: duration is only recorded when the success/fail rid EQUALS the open start's rid; an unattributed success (rid=None) or ANY failure closes the run without recording duration. Manual-resume checks convert every action to "ign" while paused (`if self.status == "paused" and self.manual_resume: action = "ign"`), so they cannot self-resuscitate. S3 upload and prune stay outside the transaction — long network I/O under a row lock is the deadlock the comment warns about.
**Probe:** `hc/api/tests/test_ping.py::test_it_sets_last_duration`, `test_it_does_not_update_last_ping_on_rid_mismatch` (last_start preserved, no duration), `test_it_clears_last_ping_on_failure`, `test_it_handles_manual_resume_flag` (status stays paused, kind=="ign"), `test_it_uploads_body_to_s3` (>100B → object_size + put_object(code, n, data)).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "ping last_start last_start_rid manual_resume", limit: 10 });
```
Resolves line-exact: test pins test_ping.py :225-232 etc.; symbol `hc.api.models.Check.ping` :492-572.

## Verdict
Adopt the atomic state+audit commit, the rid-matched duration ladder, manual-resume-as-ignore, and post-transaction side effects. Adapt select_for_update to your ORM's row-lock primitive (or optimistic versioning), the 100-byte S3 threshold, and the every-100 prune hook. Omit the email-ping UA conventions if you have no mail intake path.
