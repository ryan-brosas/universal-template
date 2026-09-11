<!-- capsule-v2 -->
# Redirect proxy rebuild — how are Proxy-Authorization and proxy maps recomputed per hop without leaking into TLS tunnels?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How does `rebuild_proxies` re-resolve the proxy map on every redirect, and why is Proxy-Authorization header injection https-only-excluded?

## SessionRedirectMixin.rebuild_proxies
**Path/Symbol:** `src/requests/sessions.py:SessionRedirectMixin.rebuild_proxies` (:334-368).
**Signature:** `rebuild_proxies(prepared_request: PreparedRequest, proxies: dict[str, str] | None) -> dict[str, str]`.

### Decisive source
```python
new_proxies = resolve_proxies(prepared_request, proxies, self.trust_env)
if "Proxy-Authorization" in headers:
    del headers["Proxy-Authorization"]            # strip stale creds first
try:
    username, password = get_auth_from_url(new_proxies[scheme])
except KeyError:
    username, password = None, None
# urllib3 handles proxy authorization for us in the standard adapter.
# Avoid appending this to TLS tunneled requests where it may be leaked.
if not scheme.startswith("https") and username and password:
    headers["Proxy-Authorization"] = _basic_auth_str(username, password)
return new_proxies
```

**Flow:** resolve final proxy map (`utils.resolve_proxies`: request-level proxies as base + env proxies via `setdefault` when trust_env and not NO_PROXY-bypassed) → delete any inherited Proxy-Authorization header → pull user:pass embedded in THIS hop's proxy URL → re-inject as Basic header ONLY for plaintext http hops.
**Invariant:** Two-sided leak protection: (1) the header is ALWAYS stripped before re-evaluation, so credentials minted for hop-1's proxy never ride along to hop-2's different proxy; (2) https targets never get the header because CONNECT-tunneled requests would send it inside the tunnel where urllib3 already handles proxy auth itself — duplicate auth there is a leak vector. Porters who skip the del-first ordering can forward proxy creds across proxy boundaries; porters who add the header unconditionally double-auth TLS tunnels.
**Probe:** Direct tests: `tests/test_requests.py::TestRequests::test_respect_proxy_env_on_send_self_prepared_request` (:617) and `_on_send_session_prepared_request` (:624) cover env-proxy resolution through send; `grep -n 'scheme.startswith("https")' src/requests/sessions.py` → exactly 1 hit (:365).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "resolve_proxies request proxies trust_env", limit: 10 });
```

## Verdict
Adopt strip-then-maybe-reinject ordering and the https exclusion. Adapt `_basic_auth_str` to host base64 helper (keep latin-1 encoding). Omit SOCKS-specific proxy scheme handling (lives adapter-side).
