<!-- capsule-v2 -->
# Quota principal merge — when the same human arrives as user AND device, who owns the wallet?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How do you unify credit wallets when a user account and an anonymous device hash turn out to be the same spender, without double-counting history or losing pending reservations?

## Principal resolution + lock-recheck ladder
**Path/Symbol:** `backend/app/services/ai_usage.py` (`_lock_linked_principals` :344–383, `_active_principal_id` :307–332, `_merge_quota_principals` :410–471, `get_or_create_quota_principal` :473–608).
**Signature:** `_lock_linked_principals(db, *, user_id: uuid.UUID, device_hash: str | None) -> list[uuid.UUID]`; `get_or_create_quota_principal(db, *, user_id, device_hash, user_agent_hash, default_grant: int) -> tuple[uuid.UUID, AICreditWallet]`.
**Data Shape:** Link tables `AIPrincipalUser{user_id→principal_id}` and `AIPrincipalDevice{device_hash→principal_id}`; principals carry `status: active|merged` and `merged_into_id`. Wallets hold lifetime counters.

### Decisive source
```python
for _ in range(8):                       # bounded re-read loop
    linked_ids = await _linked_principal_ids(...)
    active_ids = sorted({await _active_principal_id(db, p) for p in linked_ids}, key=str)
    for principal_id in active_ids:
        if principal_id in locked_ids: continue
        await _advisory_lock(db, f"ai-quota-principal:{principal_id}")
        locked_ids.add(principal_id)
    refreshed_ids = await _linked_principal_ids(...)   # re-read AFTER locking
    if set(refreshed_active_ids).issubset(locked_ids):
        return refreshed_active_ids                     # stable ⇒ safe to merge
raise RuntimeError("AI 额度主体关联持续变化，请稍后重试")
```
Merge preserves the most generous state: `grant = max([default_grant, *(w.granted_tokens ...)])`, sums consumed/reserved/request_count, `frozen = any(w.frozen)`, re-points pending reservations, marks old rows `status="merged", merged_into_id=...`.

**Flow:** advisory-lock `ai-quota-user:{id}` + `ai-quota-device:{hash}` (sorted to avoid deadlock ordering) → walk link table → resolve merged chains via `_active_principal_id` (visited-set cycle guard) → lock each active principal → RE-READ links; only when the refreshed set is a subset of locked ids is the picture stable → >1 principal ⇒ merge into one new active principal.
**Invariant:** A merged principal row is terminal — every lookup must follow `merged_into_id` chains (cycle-guarded). Locks are taken on ALL linked principals before any mutation, and the post-lock re-read is what makes "link changed while I was locking" impossible to miss. History back-fill (`_historical_platform_usage`) seeds a NEW wallet with past platform spend so re-association can't reset the meter.
**Probe:** `backend/tests/test_ai_quota_concurrency.py::test_cross_linked_principals_merge_once_under_concurrency` (two concurrent first-touches linking user+device produce ONE merge, one wallet).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "_lock_linked_principals", limit: 5 });
// verified line-exact: ai_usage.py :344–383
```

## Verdict
Adopt lock→re-read→merge identity-resolution for any shared-quota entity model (also applies to team/workspace wallets); adapt lock-key naming and grant-max policy; omit the device-hash header plumbing specifics. Direct test coverage via the concurrency suite under real Postgres.
