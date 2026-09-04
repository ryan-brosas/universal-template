<!-- capsule-v2 -->
# Proxied request-URL shaping — when must the outbound request line carry the absolute URI?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `ext-requests`. **Question:** How does `HTTPAdapter.request_url` decide between origin-form (`/path?query`) and absolute-form URLs?

## HTTPAdapter.request_url
**Path/Symbol:** `src/requests/adapters.py:HTTPAdapter.request_url` (:565-597); helper `utils.urldefragauth` (:1122-1136); `PreparedRequest.path_url` in `src/requests/models.py:RequestEncodingMixin.path_url` (:111-130).
**Signature:** `request_url(request: PreparedRequest, proxies: dict | None) -> str`.

### Decisive source
```python
proxy = select_proxy(request.url, proxies)
scheme = urlparse(request.url).scheme
is_proxied_http_request = proxy and scheme != "https"
using_socks_proxy = False
if proxy:
    proxy_scheme = urlparse(proxy).scheme.lower()
    using_socks_proxy = proxy_scheme.startswith("socks")
url = request.path_url                          # origin-form default
if is_proxied_http_request and not using_socks_proxy:
    url = urldefragauth(request.url)            # absolute-form for http via proxy
```

**Flow:** select proxy → plaintext-http-through-proxy (non-SOCKS) gets ABSOLUTE url with auth+fragment stripped → everything else (direct, https-tunneled, socks) gets bare path_url.
**Invariant:** https through a proxy uses CONNECT tunneling so the inner request stays origin-form — sending absolute-form there leaks the full URL into the tunnel setup AND breaks signature schemes; http proxies need absolute-form because the proxy itself is the HTTP client. `path_url` guarantees a leading `/` (empty path→"/") and preserves query but never fragment/auth. `urldefragauth` keeps userinfo out of proxied requests (`rsplit("@", 1)[-1]`) and drops the fragment — credentials must not reach intermediary hops.
**Probe:** Direct tests: `tests/test_adapters.py::test_request_url_handles_leading_path_separators`; `tests/test_utils.py::test_urldefragauth` parametrized ×6 incl. `//u:p@example.com/path` → `//example.com/path`. `grep -n "is_proxied_http_request" src/requests/adapters.py` → 2 hits (:586 def, :594 use).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-requests", query: "request_url proxied urldefragauth", limit: 10 });
```

## Verdict
Adopt the two-form decision table and credential-stripping absolute-form builder. Adapt to host's proxy/tunnel mechanics. Omit SOCKS nuance only if host has no SOCKS support.
