<!-- capsule-v2 -->
# Slack Signature Verification — which checks make an interactivity webhook replay-proof?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What is the complete verify ladder for Slack's `v0=` HMAC scheme, and why must BOTH signature and freshness be enforced?

## v0:HMAC over raw body + 5-minute staleness window, boolean-not-raise
**Path/Symbol:** `packages/python/awaithumans/server/channels/slack/signing.py` — `verify_signature` (:27–67); constant `utils/constants.py:SLACK_SIGNATURE_MAX_AGE_SECONDS=300`.
**Signature:** `verify_signature(*, body: bytes, timestamp: str | None, signature: str | None, signing_secret: str) -> bool`.
**Data Shape:** signed message = `b"v0:" + timestamp.encode() + b":" + raw_body`; expected header = `"v0=" + hexdigest`; raw BYTES of the body are required (parsed form data cannot be verified).

### Decisive source
```python
if not timestamp or not signature or not signing_secret:
    return False
try:
    ts_int = int(timestamp)
except ValueError:
    return False
# Reject stale requests — prevents replay attacks.
if abs(time.time() - ts_int) > SLACK_SIGNATURE_MAX_AGE_SECONDS:
    return False
basestring = b"v0:" + timestamp.encode() + b":" + body
expected = ("v0=" + hmac.new(signing_secret.encode(), basestring,
                             hashlib.sha256).hexdigest())
return hmac.compare_digest(expected, signature)
```

**Flow:** missing pieces → False; non-integer timestamp → False; |now − ts| > 300s (FUTURE timestamps too — test-pinned) → False; constant-time digest compare → verdict.
**Invariant:** BOTH checks required ("We verify the signature AND reject requests older than 5 minutes... Both checks are required") — signature alone doesn't stop replays, freshness alone doesn't stop forgeries. Function returns False instead of raising: "the caller decides what to do." The timestamp string is embedded in the HMAC pre-image, so it cannot be rotated without breaking the signature.
**Probe:** `packages/python/tests/slack/test_signing.py` (:21 valid passes, :28 tampered body, :38 wrong secret, :45 stale rejected, :53 future-timestamp rejected, :60 missing fields, :71 non-integer ts).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "verify_signature SLACK_SIGNATURE_MAX_AGE_SECONDS compare_digest", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the full ladder verbatim including the abs() future-timestamp rejection and boolean-return contract. Adapt only the max-age constant per gateway behavior. Omit nothing — each rung has a dedicated upstream test.
