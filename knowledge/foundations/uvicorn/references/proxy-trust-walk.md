<!-- capsule-v2 -->
# Proxy trust walk — why is X-Forwarded-For scanned in REVERSE, and what makes a host "trusted"?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** How does ProxyHeadersMiddleware pick the client IP from a chained header, and how are IPs/networks/literals classified once?

## Rightmost-untrusted wins; all-trusted ⇒ leftmost; lru_cache on membership
**Path/Symbol:** `uvicorn/middleware/proxy_headers.py` — `get_trusted_client_address` (:170–187), `_TrustedHosts.__init__` (:104–148), cached membership :147–163, scheme rewrite :44–52.
**Signature:** `def get_trusted_client_address(self, x_forwarded_for: str) -> tuple[str, int]`; `__contains__(self, host: str | None) -> bool`.
**Data Shape:** three disjoint sets: `trusted_literals:set[str]`, `trusted_hosts:set[IPv4Address|IPv6Address]`, `trusted_networks:set[IPv4Network|IPv6Network]`; `always_trust = trusted_hosts in ("*", ["*"])`.

### Decisive source
```python
# :176-187 — each proxy APPENDS, so walk right-to-left
if self.always_trust:
    return _parse_host_port(x_forwarded_for_hosts[0])
for host_port in reversed(x_forwarded_for_hosts):
    host, port = _parse_host_port(host_port)
    if host not in self:
        return host, port            # first UNTRUSTED hop = the client
return _parse_host_port(x_forwarded_for_hosts[0])   # all trusted ⇒ client was a proxy too
```
```python
# :147 + :155-158 — membership is hot: cache it, but never cache absurd keys
self._trusts = functools.lru_cache(maxsize=4096)(self._compute_trust)
...
if len(host) > 253:      # longer than any DNS name; don't pin the cache
    return self._compute_trust(host)
```

**Flow:** middleware (OUTERMOST via Config.load) intercepts non-lifespan scopes → if the DIRECT peer (`scope["client"]`) is trusted: last `x-forwarded-proto` rewrites scheme (`http→http/ws→wss` via `.replace("http","ws")`; only those four values accepted) and the XFF chain is walked right-to-left for the first entry NOT in the trust set — that's the real client; if every hop is trusted, fall back to the LEFTMOST (client-of-clients). Empty/absent XFF leaves scope untouched. Malformed entries parse to `(value, 0)` rather than raising.
**Invariant:** Trust decision uses the TRANSPORT peer, never a header value — header-only trust is spoofable. Invalid inputs degrade to literals/no-op instead of 500s. The lru_cache is per-middleware-instance and bounded (4096) with an explicit oversize-key bypass.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'reversed(x_forwarded_for_hosts)' uvicorn/uvicorn/middleware/proxy_headers.py"` → 1; `bash -c "grep -c 'x_forwarded_for_hosts\[0\]' uvicorn/uvicorn/middleware/proxy_headers.py"` → 2; `bash -c "grep -cF 'trusted_hosts in (\"*\", [\"*\"])' uvicorn/uvicorn/middleware/proxy_headers.py"` → 1. Behavioral pins: `tests/middleware/test_proxy_headers.py:test_proxy_headers_multiple_proxies_with_ports` :447, `test_proxy_headers_haproxy_behind_alb` :628. REAL RUNNER green (261 passed incl. this suite).
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"x-forwarded-for trusted hosts reverse walk untrusted","limit":5,"detail":"ids"}` → ranks the proxy-headers direct tests line-exact.
**Verdict:** Adopt reverse-walk + transport-peer gate verbatim (security-bearing). Adapt parsing leniency at your peril. Omit IPv4/IPv6 set-split rationale comments.

