<!-- capsule-v2 -->
# safe-http SSRF guard — how do audit scripts fetch untrusted URLs without becoming an internal-network proxy?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What exact guards wrap every network fetch, and why must redirects be followed manually instead of via `allow_redirects=True`?

## Shared hardened request primitive
**Path/Symbol:** `scripts/lib/safe_http.py:safe_request` (:127-193), helpers `assert_safe_url` (:79-104), `_is_blocked_ip` (:67-76), `_consume_capped` (:107-124).
**Signature:** `safe_request(method, url, *, headers=None, timeout=15, allow_redirects=True, max_redirects=5, max_response_bytes=5*1024*1024, stream=False, session=None, **kwargs)`.
**Data Shape:** Returns a `requests.Response`; raises `SafeHTTPError(RequestException)` on policy blocks, size overflow (`Response exceeded N byte safety limit`), or `TooManyRedirects`.

### Decisive source
```python
kwargs["verify"] = True                      # TLS verification is NOT caller-overridable
for _ in range(max_redirects + 1):
    response = requester.request(method, current, ..., allow_redirects=False, stream=True, **kwargs)
    ...
    next_url = assert_safe_url(urljoin(current, location))   # EVERY hop re-validated
    if response.status_code == 303 and method not in ("GET", "HEAD"):
        method = "GET"; kwargs.pop("data", None); kwargs.pop("json", None)
```

**Flow:** normalize scheme-less URLs to https → reject non-http(s) schemes/hostless URLs → resolve DNS and block private/loopback/reserved/link-local/multicast/unspecified IPs (6 `ip.is_*` checks) → send with forced `verify=True`, manual redirect loop → each hop's Location is `assert_safe_url`'d again → 303 downgrades non-GET/HEAD to GET dropping body kwargs → HEAD responses closed-and-returned unconsumed; GET bodies streamed through `_consume_capped` (64KB chunks) so oversized payloads abort mid-read.
**Invariant:** A redirect must never launder a blocked destination — validation happens PER HOP before the next request, not once at entry. Porters who switch to `allow_redirects=True` reintroduce SSRF via open redirects.
**Probe:** `grep -c 'assert_safe_url(' scripts/lib/safe_http.py` (= 2: entry + redirect hop); `grep -cF 'kwargs["verify"] = True' scripts/lib/safe_http.py` (= 1); `grep -c 'ip\.is_' scripts/lib/safe_http.py` (= 6).
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"safe_request assert_safe_url blocked","limit":5}'` resolves `scripts/lib/safe_http.py` line-exact.

## Verdict
Adopt the per-hop revalidation ladder, IP blocklist classes, forced-TLS, and byte cap verbatim for any agent-side fetcher; adapt timeout/cap constants to host policy; omit the browser UA masquerade (`Mozilla/5.0 compatible; AgenticSEOSkill/1.0`) if your host wants honest bot identity. Direct tests: no upstream suite imports this module directly — behavior pinned by the probes above (executed green @69199160) plus every downstream script depending on it.
