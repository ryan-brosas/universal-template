<!-- capsule-v2 -->
# Reservation expiry sweeper — reclaiming holds from dead workers without a scheduler

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** Who releases token reservations whose worker died mid-call, and how do expired holds still charge the spend that DID happen?

## Piggy-backed SKIP LOCKED sweep + rollover-aware expiry
**Path/Symbol:** `backend/app/services/ai_usage.py`: `release_expired_token_reservations` :1052–1084, `async_reservation_is_pending` :1086–1118 (worker-side liveness gate), `reservation_expiry_for_policy` :186–199.
**Signature:** `release_expired_token_reservations(db, *, limit: int = 100) -> int`; `async_reservation_is_pending(db, reservation_id) -> bool`.
**Data Shape:** Expiry: sync modules 1h; async tasks 6h BUT clamped to next policy-timezone midnight (`min(6h, until_rollover)`) so a reservation can never straddle its usage_date.

### Decisive source
```python
reservations = ... select(AITokenReservation).where(
        status == "pending", expires_at <= utcnow())
    .order_by(expires_at.asc()).limit(max(1, min(limit, 1000)))
    .with_for_update(skip_locked=True)          # multi-worker safe, no contention
for r in reservations:
    released = await settle_token_reservation(db, reservation_id=r.id,
        actual_tokens=0, succeeded=False, charge_recorded_progress_on_error=True)
```
Liveness gate used by every async task stage:
```python
return bool(reservation and reservation.status == "pending"
            and reservation.expires_at > datetime.utcnow()
            and reservation.usage_date == usage_date_for_policy(policy))  # date rollover kills it too
```
Sweep is piggy-backed onto NEW reservations: `_reserve_platform_tokens` calls it first and commits — no cron needed.

**Flow:** any new platform reservation first sweeps ≤50 expired ones (skip_locked ⇒ concurrent requesters never fight over rows) → settle charges whatever provider stages recorded (`actual_tokens` sum survives via provider-stage ledger) with metadata `release_reason="reservation_expired"` → worker-side, every stage re-checks pending+unexpired+same-usage-date before spending.
**Invariant:** Sweeping must be bounded (`limit`) and non-blocking (SKIP LOCKED); an expired reservation can still CONSUME budget for provider work already done but can never authorize NEW spend. Midnight-clamped expiry keeps wallet/budget date arithmetic coherent across timezones.
**Probe:** `backend/tests/test_ai_quota_concurrency.py::test_expired_reservation_charges_provider_progress_already_recorded` + `::test_expired_reservation_releases_personal_and_global_holds`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "release_expired_token_reservations", limit: 5 });
// verified line-exact: ai_usage.py :1052–1084
```

## Verdict
Adopt piggy-backed skip-locked sweeps for any hold/lease table; adapt TTLs and timezone clamp; keep the liveness triple-check on worker paths. Direct tests green under real Postgres.
