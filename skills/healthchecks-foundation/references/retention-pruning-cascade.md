<!-- capsule-v2 -->
# Retention pruning ladder — pings, notifications, and flips on three different clocks

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** Why is flip deletion gated by BOTH the oldest retained ping AND a 93-day floor, and why does the hot path prune asynchronously while the batch path waits?

## Check.prune / visible_pings + prunepingsslow
**Path/Symbol:** `hc/api/models.py:prune` (:574-604), `visible_pings` (:606-609), `hc/api/management/commands/prunepingsslow.py` (:1-34), sibling `pruneobjects.py`, per-ping trigger in `ping()` (:570-572).
**Signature:** `prune(wait: bool = False) -> None`; `visible_pings -> QuerySet[Ping]`; threshold = `n_pings − project.owner_profile.ping_log_limit`.
**Data Shape:** Ping rows are numbered (`n`) not auto-id; retention = last N per check (default 100). Flip floor constant: `now() - td(days=93)` — "current month + two full previous months" of downtime data, with 3×31 accepted as simpler-and-close-enough.

### Decisive source
```python
# hc/api/models.py — the ordered deletion cascade
threshold = self.n_pings - self.project.owner_profile.ping_log_limit
if settings.S3_BUCKET:
    remove_objects(str(self.code), threshold, wait=wait)   # thread-offloaded unless slow path

self.ping_set.filter(n__lte=threshold).delete()
try:
    # Important: sort by "created", not by "id". Sorting by id may cause Postgres
    # to use the "api_ping_pkey" index, and scan a huge number of rows.
    ping = self.ping_set.earliest("created")

    self.notification_set.filter(created__lt=ping.created).delete()

    flip_threshold = min(ping.created, now() - td(days=93))
    self.flip_set.filter(created__lt=flip_threshold).delete()
except Ping.DoesNotExist:
    pass
```

**Flow:** Hot path: every 100th ping triggers prune(wait=False) inline — S3 removals run detached so the ping request returns fast; DB deletes stay bounded because they're keyed on the check. Slow path: prunepingsslow iterates checks with n_pings>100 in code order, re-verifies each row still exists before touching it, wraps check.prune(wait=True) in try/except (one bad check must not stop the sweep), and raises S3_TIMEOUT to 60 first.
**Invariant:** Notifications die at the OLDEST RETAINED PING's timestamp (a notification older than every visible ping has no UI anchor); flips need the MIN of that timestamp and the 93-day floor because downtime statistics read them — deleting flips by ping-age alone would silently truncate uptime history for quiet checks. earliest("created") over earliest("id") is a query-planner dodge, same lesson as Transport.last_ping and _get_events ordering comments ("sorting by id can cause postgres to pick api_ping.id index"). The DoesNotExist pass keeps zero-ping checks (fresh or fully pruned) harmless.
**Probe:** `hc/api/tests/test_check_model.py::test_it_prunes` (n=1 gone, n=101 kept, notifications+flip cleared), `test_it_does_not_prune_flips_less_than_93_days_old`, `test_it_does_not_prune_flips_newer_than_the_earliest_ping`, `hc/api/tests/test_prunepingsslow.py::test_it_works`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "prune threshold ping notification flip delete", limit: 10 });
```
Resolves line-exact: Check.prune :574-604.

## Verdict
Adopt count-based ping retention with the two-clock notification/flip cascade, async-vs-wait dual-mode pruning, and re-verify-before-touch batch sweeps. Adapt ping_log_limit source and the 93-day statistics window to your reporting needs. Omit the S3 leg cleanly if bodies stay in-row — but keep "delete audit rows only when their anchor event is gone".
