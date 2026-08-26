<!-- capsule-v2 -->
# Webhook Retry Queue — how do terminal callbacks reach unreliable receivers at-least-once without a broker?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you build durable outbound-webhook delivery with only a database table and a 5s asyncio loop — safe against double-dispatch and crashed dispatchers?

## Pin-and-fetch queue over a delivery table
**Path/Symbol:** `packages/python/awaithumans/server/services/webhook_dispatch.py` — `enqueue_completion_webhook` (:116–149), `_claim_due_deliveries` (:174–230), `backoff_delay` (:102–113), `_record_outcome` (:290–354), `redeliver` (:378–397); schedule in `utils/constants.py:WEBHOOK_RETRY_BACKOFF_SECONDS`.
**Signature:** `process_due_deliveries(session, *, batch_size=50) -> int`; `_claim_due_deliveries(session, *, now, limit) -> list[WebhookDelivery]`.
**Data Shape:** row = {url, body_bytes (frozen at enqueue), signature, status PENDING→SUCCEEDED/ABANDONED, attempt_count, next_attempt_at}; backoff tuple 30s→60s→2m→5m→15m→30m→1h→2h→4h→8h→24h×3; age cap 3 days from created_at.

### Decisive source
```python
# Pin: bump next_attempt_at past now so a competing scheduler can't pick up.
pinned_until = now + timedelta(seconds=WEBHOOK_DELIVERY_TIMEOUT_SECONDS)  # 10s claim window
await session.execute(
    update(WebhookDelivery).where(WebhookDelivery.id.in_(ids))
        .where(WebhookDelivery.status == PENDING)
        .where(WebhookDelivery.next_attempt_at <= now)
        .values(next_attempt_at=pinned_until, updated_at=now)
        .execution_options(synchronize_session=False))   # naive-vs-aware datetime crash guard
# Losers excluded by WHERE — they simply don't come back from the refetch:
fetched = await session.execute(select(WebhookDelivery)
    .where(WebhookDelivery.id.in_(ids))
    .where(WebhookDelivery.next_attempt_at == pinned_until))
```

**Flow:** terminal transition ⇒ enqueue row with body+HMAC frozen (retries resend byte-identical payloads so signatures stay valid) → scheduler tick selects due ids via composite (status, next_attempt_at) index → pin-forward 10s (= HTTP timeout; a crashed dispatcher's claims expire fast) → POST each (≥400 or httpx error = failure) → success SUCCEEDED (+ optional response-redaction hook), too-old ABANDONED, else next_attempt_at += backoff[attempt]. Admin `redeliver` resets any row to PENDING/due-now.
**Invariant:** body bytes persisted at ENQUEUE time, not render time. `backoff_delay` clamps overshoot to the LAST schedule entry — the age cap, not the schedule, stops retries. Enqueue happens AFTER the service commit (two awaits apart): a crash there loses the callback, accepted because long-poll callers recover independently.
**Probe:** `packages/python/tests/core/test_webhook_dispatch.py` (:129–164 HMAC shapes, :170–186 schedule progression + last-entry clamp, :189–231 signed-row enqueue, :275–447 succeeded/backoff/abandoned/skip-not-due/eventual-success/redeliver, :509–620 redact-on-success-only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "_claim_due_deliveries process_due_deliveries backoff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt pin-and-fetch claiming, frozen-body signing, clamped-backoff-plus-age-cap, and post-commit enqueue with documented loss window. Adapt the backoff curve to your SLA (keep cumulative < cap). Omit SQLite/Postgres dual-write reasoning only if single-engine.
