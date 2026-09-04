<!-- capsule-v2 -->
# Anti-SSRF fetch pipeline — how do you fetch attacker-supplied URLs without DNS-rebinding SSRF?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How does validate→pin→fetch→revalidate-each-redirect close the TOCTOU rebinding window?

## Three-phase defense: structure+DNS gate, pinned connection, manual redirects
**Path/Symbol:** `src/geo_optimizer/utils/validators.py:resolve_and_validate_url` (122–161); `src/geo_optimizer/utils/http.py:fetch_url` (224–252), `_PinnedIPAdapter` (172–196), `_fetch_with_manual_redirects` (255–387).
**Signature:** `resolve_and_validate_url(url) -> (valid, err, resolved_ip_list)`; `fetch_url(url, timeout=10, max_size=10MB) -> (response|None, error|None)`.
**Data Shape:** blocked set = explicit `_BLOCKED_NETWORKS` (RFC1918, loopback, CGNAT 100.64/10, link-local 169.254/16 incl cloud metadata, IPv6 ULA/fe80::/10 AND the whole `::ffff:0:0/96` mapped space + specific mapped loops) PLUS stdlib `is_private/is_loopback/is_link_local/is_reserved/is_multicast` fallback.

### Decisive source
```python
# validators: resolve ONCE; every returned IP must be public; unresolvable = REJECT
try:
    infos = socket.getaddrinfo(hostname, None)
except socket.gaierror:
    return False, "DNS resolution failed: hostname not resolvable", []   # fix #427 TOCTOU

# http: patched resolver reads thread-local pin so the connection dials the VALIDATED IP
def _pinned_getaddrinfo(host, port, *args, **kwargs):
    pin = getattr(_pinning_local, "pin", None)
    if pin and host == pin["host"]:
        pinned_ip = pin["ip"]
        family = socket.AF_INET6 if ":" in pinned_ip else socket.AF_INET
        return [(family, socket.SOCK_STREAM, 6, "", (pinned_ip, port or pin["port"]))]
    return _original_getaddrinfo(host, port, *args, **kwargs)
socket.getaddrinfo = _pinned_getaddrinfo   # installed once at import

# every redirect hop is a NEW target: revalidate, and rebuild the session only when IPs changed
ok, err, next_ips = resolve_and_validate_url(location)
if not ok:
    return None, f"Redirect to unsafe URL: {err}"
if next_ips != current_ips:
    session.close()
    session = create_session_with_retry(pinned_ips=next_ips)
```

**Flow:** scheme∈{http,https} → no `@` credentials → hostname not in `{localhost, metadata, metadata.google.internal, 169.254.169.254}` → single `getaddrinfo` → all IPs public → caller connects through `_PinnedIPAdapter` which sets `_pinning_local.pin` around `send()` → request made with `allow_redirects=False, stream=True`; 3xx hops loop with per-hop revalidation capped at 10 → body consumed via `_stream_response` enforcing max_size mid-chunks (Content-Length pre-checked) → encoding fallback `apparent_encoding or utf-8` when server lies (#338).
**Invariant:** The validated IP list must be the SAME addresses the socket dials — that is what kills rebinding between check and connect. Retry decorator `@with_retry` retries ONLY `Timeout/ConnectionError` with `backoff_base ** attempt` delay; never 4xx, SSRF rejects, size violations, or redirect exhaustion.
**Probe:** `tests/test_ssrf_hardening.py::TestResolveAndValidateUrl::test_dns_unresolvable_rejects` (+ `tests/test_http_retry.py`, `tests/test_security_critical.py`; `PYTHONPATH=src pytest tests/test_ssrf_hardening.py tests/test_http_retry.py tests/test_security_critical.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "resolve_and_validate_url DNS pinning", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt validate-once/pin-the-dial/revalidate-per-hop wholesale for any URL-fetching tool that accepts user URLs (auditors, scrapers, link checkers); adapt the blocklist to your cloud's metadata ranges; omit the legacy-mock `_content` isinstance dance unless you carry the same test fixtures.
