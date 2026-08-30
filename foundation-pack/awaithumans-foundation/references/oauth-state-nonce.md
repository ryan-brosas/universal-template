<!-- capsule-v2 -->
# Slack OAuth State Nonce — self-verifying CSRF state without a state table

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** How do you make OAuth `state` verifiable with zero server-side storage — and what does verify check in what order?

## nonce:ts:hmac → base64url; decode→HMAC→age ladder, False on everything
**Path/Symbol:** `packages/python/awaithumans/server/channels/slack/oauth_state.py` — design docstring (:1-14), `sign_state` (:30-37), `verify_state` (:40-68).
**Signature:** `sign_state(signing_secret: str) -> str`; `verify_state(state: str, signing_secret: str) -> bool`.
**Data Shape:** raw = `{nonce}:{ts}:{hmac_hex}` where payload = `nonce:ts`; urlsafe_b64encode, padding STRIPPED on encode and restored via `state + "=" * (-len(state) % 4)` on decode. Secret deliberately REUSED = SLACK_SIGNING_SECRET (one Slack secret to configure).

### Decisive source
```python
try:
    padded = state + "=" * (-len(state) % 4)
    decoded = base64.urlsafe_b64decode(padded).decode()
    nonce, ts, mac = decoded.rsplit(":", 2)      # rsplit: mac can't contain ':', nonce may not either
except Exception:
    return False                                  # malformed/un-decodable
expected = hmac.new(key, f"{nonce}:{ts}".encode(), hashlib.sha256).hexdigest()
if not hmac.compare_digest(expected, mac):
    return False
age = abs(time.time() - int(ts))
...
if age > SLACK_OAUTH_STATE_MAX_AGE_SECONDS:       # 600s constant
    return False
```
`abs()` means clock-skewed states from the future are also rejected.

**Flow:** start mints state (token_urlsafe(16) nonce + int(time.time())) → consent URL + cookie carry the SAME value → callback double-submits it against the cookie THEN runs this verify (see slack-oauth-install-flow capsule for the route order).
**Invariant:** empty/None inputs fail closed BEFORE decode; every failure path returns False (never raises); uniqueness comes free from the nonce (`test_each_state_is_unique`).
**Probe:** `packages/python/tests/slack/test_oauth_state.py` (`test_round_trip`:15, `test_wrong_secret_fails`:20, `test_tampered_state_fails`:25, `test_expired_state_rejected`:33, `test_malformed_state_returns_false`:48). Executed behaviorally at pin: round-trip True / wrong-secret False / +601s expiry False.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "sign_state verify_state oauth_state", limit: 5 });
```
Live rank-1/2 line-exact (:30-37, :40-68) with direct tests ranked right behind.

## Verdict
Adopt the stateless signed-state shape and the decode→HMAC→age ladder verbatim; adapt max-age to your flow's tolerance (600s here); omit the cookie double-submit only if your callback has another binding channel — this module alone does NOT protect against replay-in-same-browser.
