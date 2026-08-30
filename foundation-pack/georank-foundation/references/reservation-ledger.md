<!-- capsule-v2 -->
# Token reservation ledger — how do you pre-authorize LLM spend without a billing race?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How does a platform meter AI tokens across users so concurrent requests can never overspend a grant or a global daily budget, while every spend is attributable and reversible?

## Reservation/settlement two-phase kernel
**Path/Symbol:** `backend/app/services/ai_usage.py` (`_reserve_platform_tokens` :611–880, `settle_token_reservation` :969–1051).
**Signature:** `_reserve_platform_tokens(*, db: AsyncSession, request: Request | None, current_user: User | None, module: str, policy: dict[str, Any], input_tokens: int, reservation_tokens: int | None = None) -> AIRequestAccess`; `settle_token_reservation(db, *, reservation_id: uuid.UUID | None, actual_tokens: int, succeeded: bool, charge_recorded_progress_on_error: bool = False) -> AITokenReservation | None`.
**Data Shape:** Tables: `AITokenReservation{status: pending|settled|released, reserved_tokens, personal_reserved_tokens, global_reserved_tokens, usage_date, expires_at, event_metadata}`; `AICreditWallet{granted_tokens, consumed_tokens, reserved_tokens, request_count, frozen, version}` (per principal); `AIGlobalDailyBudget` (one row per usage_date). `AIRequestAccess` carries reservation_id + remaining back to the caller.

### Decisive source
```python
# Conditional UPDATE acts as the atomic check-and-hold; the row count IS the verdict:
wallet_update = await db.execute(
    update(AICreditWallet)
    .where(
        AICreditWallet.id == wallet.id,
        AICreditWallet.frozen.is_(False),
        AICreditWallet.granted_tokens
        - AICreditWallet.consumed_tokens
        - AICreditWallet.reserved_tokens
        >= requested_tokens,
    )
    .values(reserved_tokens=AICreditWallet.reserved_tokens + requested_tokens, ...)
    .returning(AICreditWallet.id)
)
if wallet_update.scalar_one_or_none() is None:
    await db.rollback()
    raise HTTPException(status_code=429, detail=build_quota_error_detail(...))
```
Settlement mirrors it with SQL-side clamps instead of Python arithmetic:
```python
reserved_tokens=func.greatest(0, AICreditWallet.reserved_tokens - reservation.personal_reserved_tokens),
consumed_tokens=AICreditWallet.consumed_tokens + charged_tokens,
...
consumed_tokens=func.least(AIGlobalDailyBudget.limit_tokens,
                           AIGlobalDailyBudget.consumed_tokens + charged_tokens),
```

**Flow:** estimate → `calculate_reservation_tokens` floor → advisory locks on principal → conditional UPDATE holds personal wallet THEN global budget (each may 429 with reason code) → insert pending reservation → commit → provider call → settle: release hold, charge `max(actual_tokens, module minimum)` on success / recorded-progress or 0 on error; overage above the authorized amount is preserved in `event_metadata["reservation_overage_tokens"]` rather than silently charged.
**Invariant:** Available = granted − consumed − reserved is only ever mutated by single-statement conditional UPDATEs inside transactions — never read-modify-write in Python. Personal and global holds are released independently (either may be zero). Charge never exceeds authorized without an audit metadata trail.
**Probe:** `backend/tests/test_ai_quota_concurrency.py::test_concurrent_personal_reservations_cannot_exceed_grant` (N parallel reservations of a near-exhausted grant: exactly the affordable subset succeeds).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "settle_token_reservation", limit: 10, fields: ["signature", "name", "file"] });
// verified line-exact: ai_usage.py :969–1049
```

## Verdict
Adopt the two-phase reserve→settle ledger with conditional-UPDATE holds for any prepaid-metered resource; adapt table names, policy fields, and reason-code copy; omit the Chinese-language error guidance and admin audit-log UI wiring. Direct tests: full concurrency suite green under real Postgres.
