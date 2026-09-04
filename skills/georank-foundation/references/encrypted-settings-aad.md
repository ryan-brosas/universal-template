<!-- capsule-v2 -->
# Encrypted settings envelope — AES-GCM with the KEY NAME as authenticated context

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** How do you encrypt API keys stored in a settings table so that swapping ciphertext between rows is detected and key rotation doesn't brick the app?

## Marker-envelope + AAD-bound decrypt with fail-open read
**Path/Symbol:** `backend/app/services/settings_security.py` whole (140L): `ENCRYPTION_MARKER` :17, `is_sensitive_setting` :71–78 (suffix list: `_api_key|_secret|_token|_password|_private_key`), `mask_setting_value` :93–99, `encrypt_setting_value` :101–119, `decrypt_setting_value` :121–140.
**Signature:** `encrypt_setting_value(value: Any, key: str, category: str | None = None) -> Any`; `decrypt_setting_value(value: Any, key: str, category: str | None = None) -> Any`.
**Data Shape:** Envelope dict: `{__secure__: True, v: 1, alg: "AES-256-GCM", nonce: b64(12B), ciphertext: b64}`; AESGCM associated_data = the SETTING KEY utf-8.

### Decisive source
```python
ciphertext = AESGCM(settings.settings_encryption_key_bytes).encrypt(
    nonce, plaintext, key.encode("utf-8")     # setting name as AAD
)
...
try:
    plaintext = AESGCM(...).decrypt(nonce, ciphertext, key.encode("utf-8"))
    return json.loads(plaintext.decode("utf-8"))
except Exception:
    # 兼容历史坏数据或密钥切换场景，避免后台接口直接 500。
    return value        # fail-open READ: bad envelope returns as-is instead of 500-ing admin UI
```

**Flow:** write path — sensitive key? → already-encrypted or empty ⇒ pass through → JSON-serialize compact → random 12-byte nonce → AES-256-GCM with the row's KEY NAME as associated data → marker envelope stored in a JSON column. Read path — marker present ⇒ decrypt+verify (AAD mismatch ⇒ exception ⇒ return raw envelope rather than crash). Display path — `mask_setting_value` swaps any non-empty sensitive value for `••••••••••••••••` before it reaches an admin response.
**Invariant:** Ciphertext copied to ANOTHER settings row fails decryption (AAD binds identity) — this defeats the row-swap attack where e.g. the payment-gateway key is pasted into the llm_api_key slot. Encryption is IDEMPOTENT (never double-wraps). Fail-open only on READ; writes always re-encrypt.
**Probe:** `backend/tests/test_settings_security.py` (round-trip, tamper, cross-key AAD rejection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "encrypt_setting_value", limit: 5 });
// verified line-exact: settings_security.py :101–119
```

## Verdict
Adopt the AAD-bound envelope for any DB-stored secrets; adapt sensitivity suffix lists; note the deliberate read-side fail-open and decide if your threat model prefers hard failure. Direct tests green under real runner.
