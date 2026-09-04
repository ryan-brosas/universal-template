<!-- capsule-v2 -->
# Usage recording & settlement coupling — one event, one wallet mutation, no double counting

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** After a provider call, how do the usage EVENT row and the reservation SETTLEMENT stay consistent — including error paths that still bill?

## record_ai_usage → settle → event.total reconciliation
**Path/Symbol:** `backend/app/services/ai_usage.py`: `record_ai_usage` :1281–1372, `record_async_task_usage` :1375–1418 (reconstructs access from a bare reservation), `record_browser_direct_usage` :1421–1455 (BYOK stats never touch quota), `MODULE_CHARGE_MIN_TOKENS` :44–50.
**Signature:** `record_ai_usage(db, access: AIRequestAccess, *, output_text="", status_value="success", error_code=None, metadata=None, charge_recorded_progress_on_error=False, charge_reserved_tokens_on_error=False) -> AIUsageEvent`.
**Data Shape:** `AIUsageEvent{user_id, principal_id, reservation_id, module, provider_source, provider, model, input_tokens, output_tokens, total_tokens, status, error_code, event_metadata}`; `UserDailyUsage` per user+date for metered modules only.

### Decisive source
```python
if access.provider_source == "platform" and access.reservation_id:
    settlement_tokens = total_tokens
    if status_value != "success" and charge_reserved_tokens_on_error:
        settlement_tokens = max(settlement_tokens, access.reserved_tokens)  # cancelled stream still paid
    settled_reservation = await settle_token_reservation(...)
    if settled_reservation and settled_reservation.charged_tokens > 0:
        total_tokens = settled_reservation.charged_tokens   # event reflects what was CHARGED
        event.total_tokens = total_tokens
```
```python
# BYOK browser-direct events are useful for admin visibility, but they do
# not consume platform daily quota.  provider_source="user_byok_browser_direct"
```

**Flow:** estimate output from real text → insert event → platform+reservation ⇒ settle (charge floor = module minimum; overage recorded in metadata; error paths choose between free / recorded-progress / full-reserved charge via two booleans) → daily-usage row updated ONLY for `metered_modules` on success. Async twin rebuilds an AIRequestAccess from just a reservation id so workers can record without carrying the original request.
**Invariant:** The event's `total_tokens` converges to the SETTLED charge, not the raw estimate — analytics and billing can never disagree. Browser-direct/BYOK events carry `provider_source` markers that exclude them from every quota query (`_historical_platform_usage` filters `provider_source == "platform"`). Module charge floors make tiny successful calls still cover fixed costs.
**Probe:** `backend/tests/test_ai_quota_concurrency.py::test_actual_overage_saturates_global_budget_and_blocks_followup_calls` + `::test_cancelled_stream_can_conservatively_charge_full_reservation`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "record_ai_usage", limit: 5 });
// verified line-exact: ai_usage.py :1281–1372
```

## Verdict
Adopt settle-then-reconcile-event ordering for any metered call path; adapt charge-floor tables and error-charge policy flags; keep provider_source as the partition key between paid/free traffic.
