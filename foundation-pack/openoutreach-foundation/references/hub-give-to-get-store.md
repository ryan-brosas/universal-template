<!-- capsule-v2 -->
# Hub give-to-get contacts store — how do you run a data cooperative without letting it break the product?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you structure "ask the shared cache before paying, contribute after a paid hit" so outages, missing tokens, and jurisdiction rules all degrade to no-ops?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/contacts/service.py:resolve` (:36-67), `contribute` (:70-108), `register_operator` (:125-164), `_mint` (:178-187), `_build_fields` (:232-243).
**Signature:** `resolve(lead) -> str | None`; `contribute(lead, emails: list[str], origin: str) -> None`; `register_operator() -> bool`.
**Data Shape:** resolve → email or None (miss / no token / outage all collapse to None ⇒ caller falls back to the paid provider). contribute record: `{public_identifier, country_code, emails, origin, client_sha, client_dirty?, embedding?}`.

### Decisive source
```python
# resolve: both hit (200) and miss (404) are expected; anything else → None, stay quiet
if resp.status_code not in (200, 404):
    return None   # unexpected → fall back to BetterContact

def contribute(lead, emails, origin):
    if is_eea_located(SiteConfig.load().country_code): return   # operator jurisdiction gate
    emails = [e for e in emails if e]
    if not emails: return
    if is_eea_located(lead.country_code): return                # lead jurisdiction gate
    ...token? _send : _register (mint folded into first contribution)
```

**Flow:** buy step calls `resolve` before paying; a hit writes the address and skips the provider job + credit entirely. A paid hit later contributes the found email back (`ORIGIN_BETTERCONTACT`), attaching the cached embedding vector when present — never re-deriving it.
**Invariant:** Identity ≠ entitlement: `register_operator()` mints a token from the operator's email at onboarding *regardless of jurisdiction and without any contribution*, because an install that cannot contribute still needs quotas/metering/balance visibility; `_register` remains as the compatibility path for installs whose hub was down at onboarding. The EEA/UK/CH gate is enforced server-side (the only trusted boundary); the client-side check merely avoids a pointless round trip. Every request carries a product User-Agent with build sha, and every contributed record carries client_sha (+client_dirty only when determined — never a reassuring False).
**Probe:** `tests/contacts/test_service.py::TestResolve` (:51-97), `TestContribute` (:98-197), `TestRegisterOperator` (:198-277), `TestBuildReporting` (:278+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "contribute", limit: 5 });
```

## Verdict
Adopt resolve-before-pay ordering, best-effort swallow-and-fall-back for every cooperative call, identity-minted-at-onboarding separate from contribution, and dual jurisdiction gates (operator + subject). Adapt endpoint/auth shape; omit the specific hub API contract and the newsletter separation notes unless you run a cooperative too.
