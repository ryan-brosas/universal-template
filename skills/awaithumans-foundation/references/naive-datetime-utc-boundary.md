<!-- capsule-v2 -->
# Naive-Datetime UTC Boundary — SQLite drops tzinfo and local time lies

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-agents-awaithumans`. **Question:** Where must DB-loaded datetimes be coerced before crossing a channel boundary, and what breaks if they aren't?

## Write-path pair: utils/time.to_utc_unix (epoch out) + schemas/_datetime.utc_iso (string out)
**Path/Symbol:** `packages/python/awaithumans/utils/time.py` — trap docstring (:1-17), `to_utc_unix` (:24-33); twin `server/schemas/_datetime.py` — `utc_iso` (:21-34); consumers: handoff expiry (`handoff_url.task_handoff_expiry`), response serializers (`schemas/task.py:131,:142`, `schemas/audit.py:29`).
**Signature:** `to_utc_unix(dt: datetime) -> int`; `utc_iso(dt: datetime | None) -> str | None`.
**Data Shape:** naive ⇒ ASSUMED UTC (the write path guarantees it); aware ⇒ converted; iso output replaces `+00:00` with `Z`.

### Decisive source
```python
# utils/time.py docstring: calling .timestamp() directly on a naive datetime makes
# Python interpret it as LOCAL time, silently shifting Unix seconds by the local
# offset ... For users east of UTC this shifts email-handoff URL expiry into the
# PAST at creation time — a freshly issued 10-minute link is born already expired.
if dt.tzinfo is None:
    dt = dt.replace(tzinfo=timezone.utc)
return int(dt.timestamp())

# schemas/_datetime.py: Python emits `+00:00`; the web convention is `Z`.
return dt.isoformat().replace("+00:00", "Z")
```

**Flow:** service writes `datetime.now(timezone.utc)` → SQLite stores naive → read-back has no tzinfo → EVERY boundary crossing (signed URL expiry, webhook payload, dashboard JSON) must pass through one of these two helpers → naive re-stamped as UTC, aware converted, serialized with Z so browser `new Date(...)` parses correctly (±14h drift otherwise).
**Invariant:** never call `.timestamp()` or `.isoformat()` raw on a value loaded from SQLModel+SQLite; the fix lives at serialization boundaries because that's where the loss of tzinfo becomes observable.
**Probe:** `packages/python/tests/utils/test_time.py` (`test_naive_datetime_is_interpreted_as_utc`:40 runs under a Lagos TZ fixture, `test_url_expiry_is_in_future_for_fresh_short_task`:54). Executed behaviorally at pin: `to_utc_unix(datetime(2026,1,1))` = 1767225600 IDENTICAL under TZ=Asia/Tokyo after tzset().

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-awaithumans", query: "to_utc_unix naive datetime timestamp", limit: 4 });
```
Live rank-3 line-exact (:24-33); rank-1 shows the Postgres-side `_patch_naive_timestamp_columns` sibling in db/connection.py.

## Verdict
Adopt both boundary helpers and the naive-means-UTC convention; adapt output format to your clients (keep Z); omit the Postgres column-patching plane only if you're genuinely SQLite-only — note its existence either way.
