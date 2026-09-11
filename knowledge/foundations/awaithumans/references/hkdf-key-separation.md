<!-- capsule-v2 -->
# HKDF Key Separation — how does one operator secret back five unrelated crypto primitives safely?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How should every signing/encryption primitive derive its key so a leak of one never crosses to another — and what does the base64 decode path get wrong?

## Channel-scoped HKDF-SHA256 from one PAYLOAD_KEY
**Path/Symbol:** `packages/python/awaithumans/utils/webhook_signing.py:_decode_payload_key/_root_key/_hmac_key` (:63–125) + `sign_body/verify_signature` (:128–162); siblings: `server/core/auth.py` (dashboard sessions), `server/core/slack_handoff.py` + `server/core/email_handoff.py` (signed handoff URLs), `server/channels/email/magic_links.py` (action tokens), `server/core/encryption.py` (AES-GCM at-rest).
**Signature:** `HKDF(algorithm=SHA256(), length=32, salt=<channel-salt>, info=b"v1").derive(root_key)`; salts: `b"awaithumans-webhook-v1"`, `...-dashboard-session`, `...-slack-handoff`, `...-email-handoff`, `...-email-magic-links`.
**Data Shape:** root = AWAITHUMANS_PAYLOAD_KEY, 32 raw bytes as urlsafe-or-standard base64 with auto-padding; webhook header = `sha256=<hex>`; session cookie = base64url(mac||body); magic token = base64url(mac||json).

### Decisive source
```python
def verify_signature(*, body: bytes, signature: str | None) -> bool:
    if not signature:
        return False                                   # fail closed
    expected = sign_body(body)
    if hmac.compare_digest(signature, expected):
        return True
    # Tolerate header-value-without-prefix (some routing layers strip).
    return hmac.compare_digest(signature, expected.removeprefix("sha256="))
```
Decode ladder shared by ALL consumers (must match `server.core.encryption.get_key` byte-for-byte or the same env var yields different keys per primitive):
```python
padded = raw + "=" * (-len(raw) % 4)
try:    decoded = base64.urlsafe_b64decode(padded)
except Exception:
    try:    decoded = base64.b64decode(padded, validate=True)   # validate=True rejects urlsafe chars
    except Exception: decoded = None
if len(decoded) != 32: raise PayloadKeyInvalidError(...)
```

**Flow:** read env once (`@lru_cache(maxsize=1)`) → strict decode (urlsafe first, standard+validate fallback; explicit length check catches copy-paste truncation) → per-primitive HKDF subkey → sign. Bumping an `info` tag is a VERSIONED BREAKING CHANGE — old signatures stop verifying by design.
**Invariant:** the same root key never signs two primitives (channel-scoped salt); verification is constant-time and prefix-tolerant but missing ⇒ fail closed; Slack inbound signatures additionally reject |now − ts| > 300s BOTH DIRECTIONS (replay AND future-stamped) before HMAC — `channels/slack/signing.py`, pinned by `tests/slack/test_signing.py` (:52–66 stale/future).
**Probe:** `tests/core/test_webhook_dispatch.py:129–164` (prefixed hex, bare hex, wrong sig, missing header, body-change invalidates), `tests/auth/test_slack_handoff_signing.py` (:38–111 field-tamper/expiry/length), `tests/email/test_magic_links.py` (:20–150 roundtrip/fresh-jti/tamper/TTL), TS parity via `tests/idempotency.test.ts` for canonical JSON.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "HKDF derive key webhook signature", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one-root-key + per-primitive-HKDF, the dual-decoder, fail-closed constant-time verify with prefix tolerance, and bidirectional timestamp windows on inbound webhooks. Adapt salt strings/version tags to your product names. Omit nothing here — this is the repo's most directly portable security seam.
