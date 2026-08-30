<!-- capsule-v2 -->
# Service Key Hash-at-Rest — show-once raw keys with ULID-shaped ids

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What must a machine-credential service do so a DB leak yields no usable keys and revocation never leaks existence?

## SHA-256(raw) only; same NotFound error for miss AND revoked; idempotent revoke
**Path/Symbol:** `packages/python/awaithumans/server/services/service_key_service.py` — `_hash` (:34-36), `_ulid` (:39-48), `create_service_key` (:54-77), `verify_service_key` (:80-95), `list_service_keys` (:98-106), `revoke_service_key` (:109-119). Constants: prefix `ah_sk_`, RAW_BYTES=20, DISPLAY_PREFIX_LENGTH=12, MAX_NAME_LENGTH=80 (`utils/constants.py:307-309`).
**Signature:** `create_service_key(session, *, name) -> tuple[str, ServiceAPIKey]` (raw shown ONCE, never stored); `verify_service_key(session, raw_key) -> ServiceAPIKey` (touches last_used_at).
**Data Shape:** row stores `key_hash=sha256hex`, `key_prefix=raw[:12]` (display only), timestamps; NO plaintext column.

### Decisive source
```python
row = result.scalar_one_or_none()
if row is None or row.revoked_at is not None:
    raise ServiceKeyNotFoundError()     # SAME error both cases — no existence leak
...
# revoke: idempotent by design
if row.revoked_at is None:
    row.revoked_at = datetime.now(timezone.utc)
    ...commit...
return row                              # already-revoked returns row unchanged
```

**Flow:** create → validate name length → mint `ah_sk_ + token_hex(20)` → store hash + 12-char display prefix + ULID-shaped id → return raw once. Verify → hash lookup → revoked counts as missing → bump last_used_at + commit. Revoke → set timestamp if unset → return row either way.
**Invariant:** verification compares hashes, never stored plaintexts (none exist); the twin `_ulid` generator mirrors embed `_token_id` exactly (13-hex ms timestamp + 16-hex random, 29 chars) — sortable ids across both services by convention, not shared code.
**Probe:** `packages/python/tests/embed/test_service_key_service.py` (`test_create_returns_raw_key_once`:38, `test_verify_rejects_revoked_key`:58, `test_list_excludes_revoked_by_default`:65, `test_create_rejects_oversize_name`:80) — suite green at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "create_service_key verify_service_key _ulid key_hash", limit: 4 });
```
Live rank-1/2/4 line-exact (_ulid :39-48, verify :80-95, create :54-77).

## Verdict
Adopt hash-only storage, unified miss/revoked error, and idempotent revoke; adapt prefix/lengths to your namespace (keep the display-prefix short enough to be safe to log); omit last_used_at tracking if you have no rotation UX that needs it.
