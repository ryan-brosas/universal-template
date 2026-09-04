<!-- capsule-v2 -->
# ITPM/OTPM reservation ledger — how do you enforce SEPARATE input/output token-per-minute limits when actual usage is only known after the call?

**Source:** litellm (MIT), `litellm_internal_staging@f005afa1`; Codebase Memory `ext-litellm`. **Question:** reserve estimated input/output tokens pre-call, reconcile to actuals post-call, refund on failure — without stranding reservations or letting forged metadata bypass limits.

## itpm-otpm-reservation-ledger
**Path/Symbol:** `litellm/router_utils/pre_call_checks/io_token_rate_limit_check.py` (`io_token_pre_call_check` :396-455, `async_io_token_pre_call_check` :458-524, `io_token_reconcile_success` :527+, `io_token_refund_failure` :639, `refund_stale_reservation_before_retry` :663-687, `set_io_token_rate_limit_request_kwargs` :47-61).
**Signature:** `io_token_pre_call_check(dual_cache: DualCache, deployment: dict) -> dict | None`; reservation stash keys: `ITPM_RESERVED_KEY="_litellm_itpm_reserved"`, `OTPM_RESERVED_KEY`, `ITPM_CACHE_KEY`, `OTPM_CACHE_KEY` (:41-44). Cache keys from `RouterCacheEnum.ITPM/OTPM.value.format(id=..., model=..., current_minute="%H-%M")`.
**Data Shape:** reservation tuple `(itpm_reserved:int, otpm_reserved:int, itpm_cache_key:str|None, otpm_cache_key:str|None)` stashed into request kwargs `metadata` AND `litellm_metadata` channels; read back by channel priority top-level metadata > litellm_metadata > litellm_params.metadata > standard_logging_object.metadata (`_reservation_channels` :276-289).

### Decisive source
```python
# _reservation_value: estimation failed → reserve a minimal 1-token slot, never the full limit
if limit is None:
    return 0
if value > 0:
    return value
# Reserve a minimal 1-token slot rather than the full limit: the latter
# would let one request whose estimate failed fill the entire bucket,
# serializing every concurrent request to the deployment until it
# completes and reconciles against actual usage.
return 1
```
(:311-321; direct test `test_estimate_failure_reserves_minimal_not_full_limit`.)

**Flow:** pre-call: estimate input tokens (`token_counter`, best-effort suppress-errors → 0) + resolve max_tokens (explicit kwarg ladder `max_tokens`→`max_completion_tokens`→`max_output_tokens` honoring explicit **0**, else model default, else 4096) → atomic INCREMENT-WITH-ROLLBACK per dimension (increment; if result `> limit`: increment back `-value` and raise RateLimitError with `num_retries=0`) → reserving OTPM failure refunds the already-made ITPM reservation before re-raising (:429-446/:504-515) → stash sentinels. Post-success: reconcile delta = `actual - reserved` against the SAME cached key stored in the sentinel (encodes the reservation's minute — survives minute-boundary spans), then ALWAYS `_clear_reservation_from_kwargs` in finally so retries/duplicate success events can't double-process. Failure: refund full reserved amounts.
**Invariant:** (1) usage without an input/output breakdown (bare `total_tokens`) is NOT "resolved" — the reservation is KEPT rather than refunded as zero (`_usage_is_present` docstring :185-199); (2) cached prompt-read tokens are EXCLUDED from billable ITPM (`max(0, prompt - cached)`); (3) security: `set_io_token_rate_limit_request_kwargs` STRIPS any client-supplied reservation sentinels first — caller-controlled proxy metadata must not be able to drive reconcile/refund against arbitrary counters or forge a bypass; (4) the contextvar pinning kwargs for the whole request lifetime is overwritten with None for non-IO deployments (pooled-resource context capture would otherwise retain messages indefinitely); (5) `refund_stale_reservation_before_retry` exists because a retry after non-RateLimitError failure would overwrite kwargs and strand deployment A's unreconciled reservation until TTL — false 429s for later traffic (its "ponytail" note flags the sync-blocking INCR tradeoff).
**Probe:** `tests/test_litellm/test_router/test_io_token_rate_limits.py` — `test_otpm_atomic_reservation_no_overshoot_under_concurrency` (:160), `test_itpm_estimate_failure_reserves_minimal_not_full_limit` (:205), `test_explicit_zero_max_tokens_does_not_reserve_otpm` (:354); suite GREEN 53/53 incl. this file at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-litellm", query: "async_io_token_pre_call_check ITPM OTPM reservation", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt reserve→reconcile-delta→refund protocol with the same-key reconciliation and the 1-token floor; adapt the estimate/max_tokens ladders to your tokenizer surface; omit the client-sentinel strip only if your metadata is server-only by construction.
