<!-- capsule-v2 -->
# SSRF-pinned provider HTTP — how do you call a user/admin-configured LLM base URL without enabling SSRF or credential leaks?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** DNS can rebind between validation and connection — what is the full defense for outbound calls to configurable provider endpoints carrying server-held API keys?

## Shape validation → resolve-and-verify → connect-time re-pin
**Path/Symbol:** `backend/app/services/provider_url_security.py` whole file (152L): `provider_endpoint_identity` :19–31, `_require_global_address` :35–39, `validate_provider_url_shape` :42–68, `_resolve_validated_addresses` :71–89, `validate_provider_base_url` :92–98, `build_provider_api_url` :101–106, `PinnedAsyncNetworkBackend` :109–134 (`connect_tcp` :112–134), `PinnedAsyncHTTPTransport` :137–141, `build_provider_http_client` :143–152. *(Line pins re-audited against source at pin `424a0cf9` 2026-08-24 — the original pass shipped a systematic mid-file drift of ~+17–20 lines below `_resolve_validated_addresses`; all ranges above verified symbol-exact by grep -n.)*
**Signature:** `validate_provider_base_url(base_url: str) -> str` (async); `PinnedAsyncNetworkBackend.connect_tcp(host, port, timeout=None, local_address=None, socket_options=None)`; `build_provider_http_client(*, timeout: float) -> httpx.AsyncClient`.
**Data Shape:** Escape hatch: `settings.ALLOW_PRIVATE_LLM_PROVIDER_URLS` (dev-only) permits http + private IPs and skips pinning. Errors: `ProviderURLValidationError(ValueError)`.

### Decisive source
```python
class PinnedAsyncNetworkBackend(AutoBackend):
    """Resolve once per connection, validate, then connect to the approved IP literal."""
    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        addresses = await _resolve_validated_addresses(host, port)   # RE-validates at connect time
        last_error = None
        for address in addresses:
            try:
                return await super().connect_tcp(address, port, ...)  # dials the IP literal
            except Exception as exc:
                last_error = exc
        raise last_error
```
and the shape gate rejects everything but clean https:
```python
if parsed.username or parsed.password: raise ...   # no credentials in URL
...
if not settings.ALLOW_PRIVATE_LLM_PROVIDER_URLS:
    if hostname == "localhost" or hostname.endswith(".localhost"): raise ...
    try: address = ipaddress.ip_address(hostname)
    except ValueError: pass
    else: _require_global_address(address.compressed)   # is_global ⇒ blocks CGNAT 100.64/10, loopback, RFC1918
```

**Flow:** validate shape (https-only by default, no userinfo/query/fragment, hostname not localhost/IP-literal must be global) → async resolve via `getaddrinfo` where EVERY resolved address must be global → build client whose transport overrides `connect_tcp` so each connection re-resolves, re-validates, and dials the validated IP literal — closing the TOCTOU rebinding window. `validate_provider_base_url` runs before every client creation; `follow_redirects=False` prevents redirect-based escape.
**Invariant:** A host that validated public may NOT be dialed if its DNS later answers private — the connect-time hook re-runs the same gate. The client also sets `trust_env=False` so proxy env vars cannot silently reroute key-bearing traffic.
**Probe:** `backend/tests/test_provider_url_security.py:30` `test_connect_backend_revalidates_dns_and_never_connects_to_rebound_private_ip` — patches `app.services.provider_url_security.socket.getaddrinfo` with TWO side-effect resolutions (public 93.184.216.34 then private 127.0.0.1), runs `validate_provider_base_url` (accept) followed by `PinnedAsyncNetworkBackend.connect_tcp` (must raise), and asserts the patched `AutoBackend.connect_tcp` AsyncMock is NEVER awaited (rebind firewall). Runner-blocked this window (no venv in inspo clone); probe SEMANTICS executed live inline at the pin with a stubbed `app.core.config.settings`: all three assertions hold (public resolution accepted, rebound-private dial raises ProviderURLValidationError, real connect never awaited).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "PinnedAsyncNetworkBackend", limit: 5 });
// live-verified rank-1 line-exact 2026-08-24: Class :109–134, connect_tcp :112–134 (BM25)
```

## Verdict
Adopt wholesale for any server that relays credentials to admin/user-supplied endpoints; adapt the private-mode escape hatch naming; omit nothing — this module is deliberately dependency-minimal (httpx/httpcore only). Direct tests green under real runner.
