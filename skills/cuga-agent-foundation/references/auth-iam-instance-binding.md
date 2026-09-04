<!-- capsule-v2 -->
# IAM token instance binding — how do you prove a cloud IAM token is scoped to THIS instance when the binding claim varies by token type?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where can an IBM-IAM-style instance binding live in the claims, and in what order must you check before rejecting?

## OIDC-discovery validation then five-claim containment ladder
**Path/Symbol:** `src/cuga/backend/server/auth/jwt_validator.py:82-186` (`validate_iam_token`) and `:189-227` (`_assert_iam_token_bound_to_instance`).
**Signature:** `async validate_iam_token(token: str, instance_id: str, *, skip_verify=False, ca_bundle=None) -> dict[str, Any]`; `_assert_iam_token_bound_to_instance(payload: dict, instance_id: str) -> None`.
**Data Shape:** Raises `ValueError` with a descriptive message on EVERY failure mode (bad JWT, missing iss, non-https iss, discovery failure, expired, issuer mismatch, not-bound); returns the decoded payload on success.

### Decisive source
```python
# jwt_validator.py:196-224 — the containment ladder (case-insensitive substring)
norm_id = instance_id.lower()
aud = payload.get("aud");  aud = [aud] if isinstance(aud, str) else aud
if isinstance(aud, list):
    for entry in aud:
        if isinstance(entry, str) and norm_id in entry.lower():
            return                                   # 1. aud list/str
for claim in ("crn", "account_id"):
    val = payload.get(claim)
    if isinstance(val, str) and norm_id in val.lower():
        return                                       # 2. crn / account_id
account = payload.get("account")
if isinstance(account, dict):
    acct_id = account.get("bss") or account.get("id") or ""
    if isinstance(acct_id, str) and norm_id in acct_id.lower():
        return                                       # 3. account.bss / account.id
sub = payload.get("sub") or ""                     # 4. sub equality-ish
if isinstance(sub, str) and norm_id in sub.lower():
    return
raise ValueError("IAM token is not bound to instance ...")
```
Validation pipeline: decode UNVERIFIED to read `iss` → normalize via `normalize_issuer_for_discovery` → fetch `<iss>/.well-known/openid-configuration` with follow_redirects → take `jwks_uri` from the document → PyJWK signature + exp + iss verification with **verify_aud=False** (the aud claim is checked later by the containment ladder against instance_id, not against an audience constant). Note the deliberate asymmetry with the static-issuer validator: here the issuer comes from the token itself, so discovery replaces configuration.

**Flow:** exchanged IAM token → unverified iss → https-normalized discovery → JWKS sig/exp/iss check → containment ladder over (aud, crn, account_id, account dict, sub) → payload returned to caller.
**Invariant:** Instance binding must be confirmed from claims BEFORE trusting the token for instance-scoped operations; because the proxy may populate any of several claims, absence in ONE claim is never grounds for rejection — only exhausting the whole ladder is. verify_aud stays off during jwt.decode or the ladder would double-check against the wrong value.

**Probe:** No dedicated unit test in tests/unit — coverage caveat: exercised via integration flows; read source when porting. The docstring enumerates the four binding shapes; treat it as the contract.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "validate_iam_token assert bound instance crn account", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the discovery-driven validation + exhaustive containment ladder + ValueError-everywhere error shape. Adapt claim names to your cloud's IAM contract. Omit entirely if your tokens always carry a single well-known audience.
