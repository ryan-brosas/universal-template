<!-- capsule-v2 -->
# SSRF-safe crawl — how does a crawler fetch arbitrary user-submitted company URLs without touching internal networks?

**Source:** GEOrank (aeo-georank) Apache-2.0 `main@424a0cf92b37ad63c94ae9dc6f39745189ab7c94`; Codebase Memory `ext-aeo-georank`. **Question:** Where must URL validation run so redirects and per-request navigation can't smuggle the crawler into private space?

## Normalize → resolve-check → per-request route interception
**Path/Symbol:** `backend/app/services/company_ingest.py` (`normalize_company_url` :97–133, `validate_public_crawl_url` :135–152, `_validate_public_hostname` :86–94) + `backend/app/tasks/crawl.py` `_crawl_page` :224–294 (`enforce_public_request` :240–257).
**Signature:** `normalize_company_url(raw_url: str) -> str` (raises ValueError); `validate_public_crawl_url(raw_url: str) -> str` (adds DNS resolution check).
**Data Shape:** Blocked: localhost/.localhost/.local/.internal hostnames; any parsed IP with `not is_global` (loopback, RFC1918, CGNAT, link-local); schemes outside http(s); userinfo in URL.

### Decisive source
```python
# crawl.py — every request the page makes is re-validated:
def enforce_public_request(route):
    request_url = route.request.url
    parsed = urlparse(request_url)
    if parsed.scheme not in {"http", "https"}:
        route.abort("blockedbyclient"); return
    try:
        # 每次网络请求重新解析，避免复用已过期的 DNS 判断。
        # (Re-resolve DNS on EVERY request — never reuse a stale allow decision.)
        validate_public_crawl_url(request_url)
    except ValueError:
        route.abort("blockedbyclient"); return
    route.continue_()
context.route("**/*", enforce_public_request)
context.route_web_socket("**/*", lambda ws: ws.close())   # websockets: closed outright
```

**Flow:** user input → normalize (scheme default https://, strip credentials, lowercase host, drop query/fragment/path-trailing-slash) → hostname sanity (no local/internal names; IP literals must be global) → getaddrinfo ALL resolved addresses must be global → Playwright context routes EVERY subresource request through the same validation (fresh DNS each time) → page loaded with a declared bot UA (`GEOrankBot/1.0`) and service workers blocked.
**Invariant:** Validation is never cached across navigations or redirect hops; the SAME function guards entry AND every runtime request. The final `page.url` is re-validated after load (redirects can move off-origin) before it's persisted as the canonical homepage.
**Probe:** `backend/tests/test_company_pipeline.py` + integration coverage of `_crawl_page` validation path (see also test_ai_client transport tests for the same policy on provider calls).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-georank", query: "validate_public_crawl_url", limit: 5 });
// verified line-exact: company_ingest.py :135–152
```

## Verdict
Adopt request-level revalidation for ANY crawler/scraper accepting user URLs; adapt blocked-name sets to your threat model; omit Playwright specifics if using fetch-style clients (then pin at connect time like ssrf-pinned-provider-http).
