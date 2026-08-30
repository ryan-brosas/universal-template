<!-- capsule-v2 -->
# Encrypted-Config List Deferral — decrypting every row just to list them is how listing dies

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you list rows whose config column is AES-encrypted when one stale-key row would otherwise 500 the whole endpoint?

## defer(raiseload=True) forces per-row loads through the loud path
**Path/Symbol:** `packages/python/awaithumans/server/services/email_identity_service.py` — rationale docstring inside `list_identities` (:81-103), `upsert_identity` (:22-71), `get_identity` (:74-78), `identity_config` (:114-116). JSON encoding handled HERE (`json.dumps(..., sort_keys=True, separators=(",", ":"))`) so callers see dicts.
**Signature:** `list_identities(session) -> list[EmailSenderIdentity]` (config column deferred); `identity_config(identity) -> dict` (the ONLY sanctioned decrypt+parse).
**Data Shape:** `transport_config` column is an `EncryptedString` JSON blob; public list views expose everything EXCEPT it.

### Decisive source
```python
select(EmailSenderIdentity).options(
    defer(EmailSenderIdentity.transport_config, raiseload=True)
)
```
Docstring: letting SQLAlchemy materialize the column runs AES-GCM decrypt on EVERY row — "a single row encrypted under a rotated or stale PAYLOAD_KEY then raises InvalidTag and kills the whole endpoint with a 500." `raiseload=True` makes accidental reads RAISE immediately instead of lazy-loading in async context (MissingGreenlet / re-triggering InvalidTag) — forcing callers through `get_identity`, where decrypt failures surface loudly at use-time.

**Flow:** dashboard list → deferred select → public-fields serialization (no decrypt) → operator edits one identity → `upsert_identity`/`get_identity` load the full row → decrypt failure is contained to THAT identity's operation.
**Invariant:** never materialize encrypted columns in bulk reads; `raiseload=True` is load-bearing — plain defer still allows accidental lazy-load attempts that fail confusingly under asyncio.
**Probe:** `packages/python/tests/email/test_identity_service.py` (`test_transport_config_encrypted_on_disk`:45 pins ciphertext-at-rest) + `tests/email/test_admin_and_action_routes.py:test_create_identity_validates_transport_config`:146.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "upsert_identity defer raiseload EncryptedString transport_config", limit: 4 });
```
Live rank-1 line-exact (:22-71) + encryption tests.

## Verdict
Adopt defer-with-raiseload around any encrypted column and the single-decode-helper rule; adapt to your ORM's equivalent (SQLAlchemy options shown); omit only if your encrypted column can't contain legacy rows encrypted under rotated keys — then you've accepted the 500 risk knowingly.
