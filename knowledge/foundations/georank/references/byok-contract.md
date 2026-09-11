<!-- capsule-v2 -->
# BYOK header contract — how do users bring their own LLM key through YOUR server without you storing it?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** What is the minimal request-header protocol for transient bring-your-own-key that blocks base-url hijacking and policy bypass?

## Header parse → allowlist → origin pin
**Path/Symbol:** `backend/app/services/ai_usage.py` `parse_byok_override` :237–296 (+ `_http_origin` :215–235, `_provider_map`, `_clean_header`).
**Signature:** `parse_byok_override(request: Request, policy: dict[str, Any]) -> AIProviderOverride | None` (raises HTTPException on policy violations).
**Data Shape:** Headers: `X-GEOrank-BYOK-Key` (≤1000), `X-GEOrank-BYOK-Provider` (≤50, default "custom"), optional `X-GEOrank-BYOK-Base-URL` (≤240), `X-GEOrank-BYOK-Model` (≤100). Returns frozen dataclass `AIProviderOverride{provider, api_key, base_url, model, source="user_byok_proxy"}`.

### Decisive source
```python
if policy.get("byok_transport_mode") == "browser_direct":
    raise HTTPException(400, "...不能通过服务端代理使用用户 API Key")   # mode forbids server proxy entirely
provider = providers.get(provider_key)
if not provider:
    raise HTTPException(400, "当前模型供应商不在后台允许的自定义 API 范围内")
base_url = header_base_url or configured_base_url
...
configured_origin = _http_origin(configured_base_url)   # (scheme, host.lower(), port w/ defaults)
requested_origin  = _http_origin(base_url)
if not configured_origin or requested_origin != configured_origin:
    raise HTTPException(400, "API Base URL 必须使用后台允许的供应商地址")   # no query/fragment/userinfo allowed either
```

**Flow:** no key header ⇒ None (platform path) → policy disallows BYOK ⇒ None → browser_direct mode ⇒ 400 → provider key must exist in admin allowlist (`allowed_byok_providers`) → user-supplied base-url must match the CONFIGURED provider origin exactly (scheme+host+port; userinfo/query/fragment rejected by `_http_origin`) → model falls back to provider default. Downstream, the override routes `_complete_with_fallback` to a raw-HTTP call and skips platform metering entirely.
**Invariant:** The API key exists only in memory for one call — never persisted, never logged; the base_url can relax path but never ORIGIN, so a stolen key header cannot be pointed at an attacker endpoint or internal host (belt: this check; suspenders: `validate_provider_base_url` DNS pinning — see ssrf-pinned-provider-http).
**Probe:** `backend/tests/test_ai_quota_rules.py::test_parse_byok_override_*` (header matrix incl. mismatched-origin rejection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "parse_byok_override", limit: 5 });
// verified line-exact: ai_usage.py :237–296
```

## Verdict
Adopt the origin-pinned BYOK header pattern for any multi-tenant LLM gateway; adapt header names and the allowlist schema; omit browser-direct transport specifics. Direct tests green in quota-rules suite.
