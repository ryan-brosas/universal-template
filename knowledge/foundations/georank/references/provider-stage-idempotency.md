<!-- capsule-v2 -->
# Provider-stage idempotency — how does a retried async task avoid paying the LLM twice?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** When a Celery worker dies after the provider call but before persisting results, how do you make the retry skip re-spending while still recording cost already incurred?

## Stage claim/complete/release over reservation metadata
**Path/Symbol:** `backend/app/services/ai_usage.py` (`claim_async_reservation_stage` :1120–1175, `complete_async_reservation_stage` :1176–1220, `release_async_reservation_stage_claim` :1221–1280); consumed by `backend/app/tasks/process.py` + `crawl.py` via `_claim_company_provider_stage` / `_release_company_provider_stage`.
**Signature:** `claim(db, *, reservation_id, stage: str, claim_id: str, lease_seconds: int = 900) -> bool`; `complete(db, *, reservation_id, stage, claim_id, actual_tokens: int) -> bool`; `release(db, *, reservation_id, stage, claim_id) -> None`.
**Data Shape:** Stages live in `AITokenReservation.event_metadata["provider_stages"][stage_key] = {status: claimed|completed, claim_id, claimed_at, tokens}`; `reservation.actual_tokens` is recomputed as the SUM of completed stages' tokens.

### Decisive source
```python
existing = dict(stages.get(stage_key) or {})
if existing.get("status") == "completed":
    return False                      # work already paid for — never redo
claimed_at = ...
if existing.get("status") == "claimed" and claimed_time > now - max(30, lease_seconds):
    return False                      # another LIVE worker owns this stage
stages[stage_key] = {"status": "claimed", "claim_id": claim_key, ...}
```
Release refuses to erase spend:
```python
# Completed entries are append-only provider spend records. A later
# persistence or dispatch failure may retry under a new stage key, but it
# must not erase cost that the provider has already incurred.
if existing.get("status") == "completed":
    return
```
Claim ids are per-attempt: `provider_claim_id = f"{self.request.id}:{self.request.retries}"`, stage keys embed it (`f"company_profile:{claim_id}"`) so a RETRY gets a fresh stage instead of colliding with its dead attempt.

**Flow:** guard reservation pending+unexpired+same-policy-usage-date → claim stage (completed ⇒ stop; live claim ⇒ stop; expired lease ⇒ take over) → run provider call → `complete` persists tokens and marks completed BEFORE the downstream DB writes → on exception release only if still `claimed` (never completed) → retry arrives with a new claim id.
**Invariant:** `actual_tokens` is append-only across retries (sum of completed stages). A crash between complete() and result-persist loses work but never money; a crash before complete() releases the stage and re-runs the provider — exactly one of the two happens per failure point.
**Probe:** `backend/tests/test_ai_quota_concurrency.py::test_completed_provider_progress_is_retained_across_retry_attempts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "claim_async_reservation_stage", limit: 5 });
// verified line-exact: ai_usage.py :1120–1175
```

## Verdict
Adopt metadata-keyed stage leases for any multi-step paid pipeline (also fits video/image generation jobs); adapt stage naming and lease length; omit the Celery-specific request-id plumbing. Direct test coverage green under real Postgres.
