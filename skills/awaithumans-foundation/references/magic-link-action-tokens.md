<!-- capsule-v2 -->
# Magic-Link Action Tokens — how does one click in an email complete a task exactly once?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What makes an emailed approval button safe against prefetch bots, forwarded-mail replay, and tampering?

## Self-verifying jti tokens + anti-prefetch POST form
**Path/Symbol:** `packages/python/awaithumans/server/channels/email/magic_links.py` — `sign_action_token` (:79–116), `verify_action_token` (:119–168); consumption table `server/db/models/consumed_email_token.py`; action route under `server/routes/email.py`.
**Signature:** `token = base64url(mac(32) || json({t,f,v,e,j,r?}))`; `verify_action_token(token) -> ActionClaim{task_id, field_name, value, expires_at, jti, recipient}`.
**Data Shape:** per-option URL `{PUBLIC_URL}/api/channels/email/action/{token}`; jti = 16 random bytes urlsafe-b64 (22 chars); TTL default 24h (`MAGIC_LINK_MAX_AGE_SECONDS`).

### Decisive source
```python
payload = {"t": task_id, "f": field_name, "v": value,
           "e": int(time.time()) + ttl,
           "j": jti or secrets.token_urlsafe(_JTI_BYTES)}
if recipient:                      # optional field keeps old-shape tokens byte-identical
    payload["r"] = recipient       # pre-feature tokens verify with recipient=None
body = _canonical(payload)         # sort_keys, no whitespace — HMAC input must be stable
mac  = hmac.new(_hmac_key(), body, hashlib.sha256).digest()
return base64.urlsafe_b64encode(mac + body).decode().rstrip("=")
```
Verify ladder: pad-b64 decode → length ≥ 34 → split mac/body → compare_digest → json → required-fields → expiry → **recipient is opt-in `.get("r")`**, never KeyError.

**Flow:** renderer mints one token PER OPTION of a switch/single-select → human clicks GET → confirmation page with a POST form (mail-client/SafeLinks/image-proxy prefetchers fire GETs constantly; only a deliberate POST submits) → route verifies → completes the task with the single-field response → inserts jti into `consumed_email_tokens` (PK conflict ⇒ second click rejected) → forwarders/replays die at the jti wall even inside TTL.
**Invariant:** HMAC key derives from PAYLOAD_KEY under the magic-link salt (see hkdf-key-separation capsule) — never the encryption key directly ("would blur two different primitives"). Token carries NO server-side state until consumed: stateless verification, DB write only at redemption.
**Probe:** `tests/email/test_magic_links.py` (:30–40 fresh-jti-per-token, :43–49 explicit-jti override, :56–78 tamper rejection, :80–108 expiry + custom TTL, :110–133 recipient roundtrip + omission⇒None, :134–150 malformed inputs).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "magic link action token jti", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt stateless mac||json tokens with jti-consumption tables, GET-confirms/POST-submits anti-prefetch, and backward-compatible optional fields. Adapt TTL and claim fields. Omit the HTML template rendering (channel surface).
