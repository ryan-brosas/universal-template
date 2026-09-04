<!-- capsule-v2 -->
# User Directory Write Funnel — where do identity invariants live when partial indexes can't express them, and how do you stop an admin from locking everyone out?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How must user create/update/delete behave so uniqueness conflicts become typed errors, half-bound identities are rejected, and the last active operator can never be demoted, deactivated, or deleted?

## One write module + pre-flight count guard
**Path/Symbol:** `packages/python/awaithumans/server/services/user_service.py` — single-funnel docstring (:1–10), `_validate_addresses` (:38–53), `_infer_conflict` (:56–68), `update_user` guard block (:222–234), `delete_user` (:281–296), `_count_active_operators` (:308–317), `_ensure_not_last_active_operator` (:320–328).
**Signature:** `create_user(session, *, email=None, slack_team_id=None, slack_user_id=None, ..., is_operator=False, active=True) -> User`; `update_user(session, user_id, **changes) -> User`; `delete_user(session, user_id) -> bool`; `_ensure_not_last_active_operator(session, user_id, *, action: str) -> None`.
**Data Shape:** address = email OR (slack_team_id AND slack_user_id); a HALF slack pair is invalid; errors are typed — `UserNoAddressError`, `UserAlreadyExistsError("email"|"slack identity"|"identity")`, `LastOperatorError(action)`.

### Decisive source
```python
# Pre-flight BEFORE applying changes: a refused patch must not leave a
# mutated row or a dirty session behind for the caller's next query.
if row.is_operator and row.active:
    demoting = changes.get("is_operator") is False
    deactivating = changes.get("active") is False
    if demoting or deactivating:
        await _ensure_not_last_active_operator(session, row.id, action=action)

async def _ensure_not_last_active_operator(session, user_id, *, action):
    active_ops = await _count_active_operators(session)   # is_operator ∧ active only
    if active_ops <= 1:
        raise LastOperatorError(action)
```

**Flow:** every writer (admin API routes, CLI, `/setup` bootstrap, task router) calls this one module → create validates addresses, hashes password, commits, maps IntegrityError through `_infer_conflict` (substring-matches the index name out of the wrapped driver error, falls back to `"identity"` so callers always get a label) → update re-validates addresses AFTER patching so no patch can strip the last address → delete/demote/deactivate of an ACTIVE operator runs the count guard first (`<= 1` raises with the action name); deleting a non-operator or inactive operator never consults it.
**Invariant:** invariants that partial UNIQUE indexes cannot express portably across SQLite/Postgres ("at least one address", "at least one ACTIVE operator") are enforced app-layer at the single write funnel — scattering writes around the funnel reintroduces divergence; inactive operator rows do NOT satisfy "at least one".
**Probe:** `packages/python/tests/users/test_security_guards.py` — full matrix executed green at pin: `test_delete_last_operator_refused`:27 (asserts `exc.value.action == "delete"`), `test_demote_last_operator_refused`:54 (`"demote"`), `test_deactivate_last_operator_refused`:63 (`"deactivate"`), `test_last_operator_guard_ignores_inactive_operators`:81 (one active + one inactive operator ⇒ delete still refused), plus the OK-sides :36/:45/:72. Address/conflict pins: `tests/users/test_user_service.py:test_update_rejects_removing_last_address`:182.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "_ensure_not_last_active_operator _count_active_operators delete_user update_user", limit: 8 });
```
Live rank −21.5/−24.61/−24.28 line-exact (:320–328, :308–317, :281–296); grep confirms exactly two guard call sites (:234 update, :292 delete) and one raise site (:328).

## Verdict
Adopt the single-write-funnel layout, the typed conflict-inference ladder, and the pre-flight last-active-operator guard verbatim (count semantics: active-only, `<= 1`, action-labeled). Adapt the address families to your identity model but keep the partial-pair-is-broken rule. Omit the guard's TOCTOU hardening at your peril — concurrent deletes of two different operators can both pass; acceptable here because operators are few and human-created, and documented as such.
