<!-- capsule-v2 -->
# Versioned AES-GCM Column Encryption — how does transparent at-rest crypto stay rotation-ready?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you encrypt sensitive DB columns transparently to service code while leaving a key-rotation path open?

## TypeDecorator over base64(key_id ‖ nonce12 ‖ ciphertext‖tag16)
**Path/Symbol:** `packages/python/awaithumans/server/core/encryption.py` — `get_key` (:51–87), `encrypt_str` (:95–101), `decrypt_str` (:104–126), `EncryptedString` (:129–157).
**Signature:** `get_key() -> bytes` (`lru_cache(maxsize=1)`); `encrypt_str(plaintext: str) -> str`; `decrypt_str(ciphertext_b64: str) -> str`; `TypeDecorator.process_bind_param / process_result_value`.
**Data Shape:** blob = `bytes([0x01]) + os.urandom(12) + AESGCM.encrypt(...)` → standard base64; key = `AWAITHUMANS_PAYLOAD_KEY`, 32 raw bytes as urlsafe-or-standard base64 (auto-padded via `raw + "=" * (-len(raw) % 4)`).

### Decisive source
```python
# We use `validate=True` on the standard decoder because the default
# silently discards non-alphabet chars (including urlsafe's `-` and `_`),
# which can produce a short result from a well-formed urlsafe key.
try:
    decoded = base64.urlsafe_b64decode(padded)
except Exception:
    try:
        decoded = base64.b64decode(padded, validate=True)
    except Exception:
        decoded = None
...
version = blob[0]
if version != _CURRENT_KEY_ID:
    raise EncryptionKeyError(
        f"Ciphertext uses key version {version}; this server only knows "
        f"{_CURRENT_KEY_ID}. Key rotation registry not yet implemented.")
```

**Flow:** bind time: None→None else encrypt_str; result time: None→None else decrypt_str. Decrypt validates length ≥ 1+12+16, rejects foreign key versions LOUDLY, lets `InvalidTag` propagate on tamper — "no silent fallback (that would defeat the point)".
**Invariant:** version byte FIRST (rotation registry slot, currently only 0x01); plaintext never touches the DB; old plaintext-schema rows FAIL decrypt rather than degrade. `reset_key_cache()` exists for tests that swap keys.
**Probe:** `packages/python/tests/slack/test_encryption.py` (:56 roundtrip, :62 fresh-nonce-per-call, :67 wrong-key fails, :75 tampered raises, :85 truncated raises, :98 wrong-version raises, :109/:116/:123 missing/malformed/short KEY errors) + integration `test_bot_token_stored_encrypted_and_read_plain` :146.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "EncryptedString encrypt_str decrypt_str get_key", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the blob layout (version byte first), the loud no-fallback decrypt contract, and the TypeDecorator binding-layer placement. Adapt the dual-decoder if you control key format end-to-end. Omit the urlsafe fallback only with a config validation that guarantees one canonical encoding.
