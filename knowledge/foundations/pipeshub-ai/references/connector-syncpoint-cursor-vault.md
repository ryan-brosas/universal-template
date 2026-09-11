<!-- capsule-v2 -->
# Sync-point cursor vault — how are delta cursors (which may embed OAuth material) stored so a leaked row is useless?

**Source:** PipesHub AI Apache-2.0 `main@c28d1336`; Codebase Memory `mnt-hdd-utopia-inspo-platforms-pipeshub-ai`. **Question:** Incremental syncs persist "sync points" per record type; some providers hand cursors that ARE secrets (Google delta links carry auth params) — what's the storage contract?

## AES-256-GCM envelope under a hashed SECRET_KEY with explicit encrypted flags
**Path/Symbol:** `backend/python/app/connectors/core/base/sync_point/sync_point.py:` (134L whole) — key grammar `_get_full_sync_point_key` (:`f"{org_id}/{connector_id}/{type}/{key}"`), constructor SECRET_KEY gate, `_encrypt_sensitive_fields/_decrypt_sensitive_fields`, `generate_record_sync_point_key(record_type, entity_name, entity_id)` → `"records/Drive/user@example.com"`.
**Signature:** `SyncPoint(connector_id, org_id, sync_data_point_type, data_store_provider)` raising `ValueError` when `SECRET_KEY` env absent; encryption service = `EncryptionService.get_instance("aes-256-gcm", sha256(SECRET_KEY).hexdigest())`.
**Data Shape:** Cursor doc `{key, value, <field>: <ciphertext>, <field>_encrypted: True}`; read path decrypts ONLY fields carrying the `_encrypted` marker.

### Decisive source
```python
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    raise ValueError("SECRET_KEY environment variable is required for encrypting sensitive sync point data")
hashed_key = hashlib.sha256(secret_key.encode()).digest()
hex_key = hashed_key.hex()
self.encryption_service = EncryptionService.get_instance("aes-256-gcm", hex_key, ...)

for field in fields_to_encrypt:
    if field in encrypted_data and encrypted_data[field]:
        encrypted_data[field] = self.encryption_service.encrypt(encrypted_data[field])
        encrypted_data[f'{field}_encrypted'] = True
```

**Flow:** connector requests its sync point by full key → store returns raw dict → decryptor walks `_encrypted`-flagged fields → connector compares cursor to remote state to decide delta vs full sync → on write, declared sensitive fields encrypted before persist. Missing env var fails construction (fail-fast at service wiring), not mid-sync.
**Invariant:** The `_encrypted` boolean rides IN the document (self-describing ciphertext — no schema migration needed when the sensitive-field list grows). Key derivation hashes the app secret rather than reusing it directly. Fail-fast on missing secret beats silently storing plaintext deltas.
**Probe:** `grep -c 'SECRET_KEY environment variable is required' app/connectors/core/base/sync_point/sync_point.py` → `1`; suite `tests/unit/connectors/core/test_sync_point.py` (31 tests) GREEN in battery.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-platforms-pipeshub-ai", query: "SyncPoint encrypt sensitive delta link", limit: 3 });
```
**Verdict:** Adopt key grammar + GCM + self-describing flag; adapt EncryptionService to host crypto lib; omit Google-delta specifics of callers.
