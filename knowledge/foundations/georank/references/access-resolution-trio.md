<!-- capsule-v2 -->
# Async access resolution trio — sync vs queued vs system-owned AI calls

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How do the three entry contexts (interactive request, user-queued task, scheduled system job) each obtain AI authorization with the right identity, metering, and BYOK rules?

## resolve_ai_access / resolve_async_ai_access / resolve_system_async_ai_access
**Path/Symbol:** `backend/app/services/ai_usage.py`: `resolve_ai_access` :836–877, `resolve_async_ai_access` :880–925, `resolve_system_async_ai_access` :928–966; docstring rationale at :884–888.
**Signature:** `resolve_async_ai_access(*, db, current_user: User | None, module, prompt_text, request=None) -> AIRequestAccess`; `resolve_system_async_ai_access(*, db, module, prompt_text) -> AIRequestAccess`.
**Data Shape:** All return `AIRequestAccess` (reservation_id present only on platform path); async floors via `estimate_async_task_tokens` (module min 10k/1.2k); labels localize error copy (`ASYNC_TASK_LABELS`).

### Decisive source
```python
"""Pre-check an async AI task before it is queued.

Async Celery jobs cannot use a browser-local BYOK value because that key is
intentionally not stored server-side. They can only run on platform quota.
"""
```
System-owned work fakes the one flag it needs:
```python
return await _reserve_platform_tokens(
    db=db, request=None, current_user=None,
    policy={**policy, "allow_anonymous_ai_usage": True},   # system job ≠ anonymous user
    input_tokens=request_tokens, reservation_tokens=request_tokens)
```
Interactive path branches BYOK first: override present ⇒ no reservation at all (user pays upstream); platform path ⇒ full reserve.

**Flow:** SYNC — parse BYOK headers; if none, mode gate (`byok_required` ⇒ 402 w/ guidance payload; unknown modes normalize to lifetime) → reserve against principal+global. ASYNC USER — same but BYOK impossible by design; reservation created BEFORE enqueue and its id travels in task args; every stage re-validates liveness. SYSTEM (e.g. `re_diagnose_all` re-scoring loop) — no user, global-budget-only hold; quota exhaustion ABORTS the batch loop with a warning rather than failing hard.
**Invariant:** A reservation is always minted in the REQUEST context (where identity lives) and consumed in worker context; async tasks must treat `async_reservation_is_pending == False` as "authorization revoked", not as an error to retry. System jobs are metered to the global budget so a scheduled sweep can never drain personal grants invisibly.
**Probe:** `backend/tests/test_ai_quota_rules.py` (mode-gate matrix) + `test_ai_quota_concurrency.py::test_expired_reservation_*` for the worker-side half.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "resolve_system_async_ai_access", limit: 5 });
// verified line-exact: ai_usage.py :928–966
```

## Verdict
Adopt the three-context split for any metered AI feature spanning HTTP + queue + cron; adapt mode names; preserve the "BYOK dies at the queue boundary" rule — it is the whole point of the async variant.
