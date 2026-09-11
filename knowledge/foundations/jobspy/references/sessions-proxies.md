<!-- capsule-v2 -->
# Sessions & proxy rotation — the two asymmetric session flavors and the create_session factory

**Source:** JobSpy MIT `main@fda080a`; Codebase Memory `JobSpy`. **Question:** How does JobSpy build HTTP sessions with proxy rotation, and why are the retry and TLS flavors deliberately asymmetric?

## Rotating sessions
**Path/Symbol:** `jobspy/util.py` — `RotatingProxySession` (32–52), `RequestsRotating` (55–86), `TLSRotating` (89–103), `create_session` (106–132), `create_logger` (19–29), `set_logger_level` (135–151).
**Signature:** `create_session(*, proxies=None, ca_cert=None, is_tls=True, has_retry=False, delay=1, clear_cookies=False) -> requests.Session`. `RotatingProxySession.__init__(proxies)`; `RequestsRotating(proxies, has_retry=False, delay=1, clear_cookies=False)`; `TLSRotating(proxies)`.
**Data Shape:** `proxies` is a str OR list OR None; `RotatingProxySession` wraps it in `itertools.cycle` (empty list/None → `proxy_cycle=None`, no rotation overhead). `format_proxy` normalizes: http/https/socks5 prefixes kept verbatim, bare strings get `http://` prepended.

### Decisive source
```python
class RotatingProxySession:
    def __init__(self, proxies=None):
        if isinstance(proxies, str):
            self.proxy_cycle = cycle([self.format_proxy(proxies)])
        elif isinstance(proxies, list):
            self.proxy_cycle = cycle([self.format_proxy(p) for p in proxies]) if proxies else None
        else:
            self.proxy_cycle = None

class RequestsRotating(RotatingProxySession, requests.Session):
    def setup_session(self, has_retry, delay):
        if has_retry:
            retries = Retry(total=3, connect=3, status=3,
                            status_forcelist=[500, 502, 503, 504, 429], backoff_factor=delay)
            adapter = HTTPAdapter(max_retries=retries)
            self.mount("http://", adapter); self.mount("https://", adapter)
    def request(self, method, url, **kwargs):
        if self.clear_cookies: self.cookies.clear()
        if self.proxy_cycle:
            np_ = next(self.proxy_cycle)
            self.proxies = {} if np_["http"] == "http://localhost" else np_   # no-proxy sentinel
        return requests.Session.request(self, method, url, **kwargs)

class TLSRotating(RotatingProxySession, tls_client.Session):
    def __init__(self, proxies=None):
        RotatingProxySession.__init__(self, proxies=proxies)
        tls_client.Session.__init__(self, random_tls_extension_order=True)
    def execute_request(self, *args, **kwargs):
        if self.proxy_cycle:
            np_ = next(self.proxy_cycle)
            self.proxies = {} if np_["http"] == "http://localhost" else np_
        response = tls_client.Session.execute_request(self, *args, **kwargs)
        response.ok = response.status_code in range(200, 400)   # widen ok to include redirects
        return response
```

**Flow:** `create_session` picks the flavor by `is_tls`; `ca_cert` → `session.verify`. `RequestsRotating` is the ONLY flavor with urllib3 `Retry` (total/connect/status=3, `status_forcelist=[500,502,503,504,429]`, `backoff_factor=delay`) mounted on http+https adapters; it overrides `request()` to rotate proxies per call and optionally clear cookies per call. `TLSRotating` is a TLS-fingerprint client with `random_tls_extension_order=True`, NO retry machinery, and patches `response.ok` to include redirects (200–399) so `raise_for_status`-style checks don't misfire.
**Invariant:** the two flavors are NOT symmetric — retry lives only where the HTTP stack supports it (requests), never in the TLS client. The sentinel `http://localhost` in the cycle means NO proxy for that request (`self.proxies = {}`) — a per-request kill switch for testing or mixed pools. Real usage picks flavor by what the SITE needs, not the default: LinkedIn calls `create_session(is_tls=False, has_retry=True, delay=5, clear_cookies=True)` (retry + cookie-clearing, not TLS).
**Probe:** no in-repo test suite; the flavor selection is exercised through `jobspy/linkedin/__init__.py` (is_tls=False, has_retry=True, delay=5, clear_cookies=True) and `jobspy/glassdoor/__init__.py` (has_retry=True) request paths.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "JobSpy", query: "create_session RequestsRotating TLSRotating RotatingProxySession", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt rotation = `itertools.cycle` + a `http://localhost` no-proxy sentinel; retry only where the HTTP stack supports it; `response.ok` widening for the TLS client. Adapt `status_forcelist`/backoff to your rate-limit profile. Omit the cookie-clearing behavior if you need to persist session cookies. Coverage caveat: no in-repo tests; verified against source + per-site call sites.
