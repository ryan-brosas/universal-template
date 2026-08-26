<!-- capsule-v2 -->
# Redirect / TrustedHost / HTTPSRedirect trio — the small redirect middlewares

**Source:** Starlette BSD-3-Clause `main@675ae768`; Codebase Memory `ext-starlette`. **Question:** What status codes and host-normalization rules do the redirect-class middleware use?

## TrustedHostMiddleware
**Path/Symbol:** `starlette/middleware/trustedhost.py:TrustedHostMiddleware.__call__` (:31-60).
**Data Shape:** patterns validated at init (`*` only as full-string or `*.`-prefix — "Domain wildcard patterns must be like '*.example.com'"); port stripped from Host header before compare; `www.` +host matching a pattern → optional 307 redirect (www_redirect=True default) preserving the full URL.
**Flow:** allow_any short-circuits entirely (zero per-request cost when unconfigured).
**Probe:** `tests/middleware/test_trusted_host.py` (3 tests incl. redirect).

## HTTPSRedirectMiddleware
**Path/Symbol:** `starlette/middleware/httpsredirect.py:HTTPSRedirectMiddleware.__call__` (:10-19).
**Data Shape:** http/ws → https/wss via dict; 307 (method-and-body-preserving); netloc keeps the port EXCEPT default ports 80/443 which are dropped after scheme swap.
**Invariant:** 307 not 301/302 — POST bodies survive the hop.
**Probe:** `tests/middleware/test_https_redirect.py`.

## RedirectResponse
**Path/Symbol:** `starlette/responses.py:RedirectResponse` (:204-214).
**Data Shape:** default status 307; location header value goes through `quote(url, safe=":/%#?=@[]!$&'()*+,;")` — an aggressive safe-list that preserves URL structure characters while escaping everything else.
**Probe:** exercised by router slash-redirect tests (`test_routing.py::test_router` :181).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-starlette", namePattern: "TrustedHostMiddleware", limit: 5 });
```

## Verdict
Adopt the wildcard grammar assertion and 307-everywhere policy. Adapt www_redirect default for API-only hosts. Omit nothing else — these are ~150 lines total.
