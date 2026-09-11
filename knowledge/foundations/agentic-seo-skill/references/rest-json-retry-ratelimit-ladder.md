<!-- capsule-v2 -->
# rest_json retry ladder — how do you retry GitHub 403 rate-limit exhaustion differently from generic 5xx backoff?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What is the exact retry/wait policy per failure class, and what envelope does every caller receive on success?

## Status-classified retry loop over safe_request
**Path/Symbol:** `scripts/github_api.py:rest_json` (:197-278); transport `lib/safe_http.py:safe_request` (see `safe-http-ssrf-guard`).
**Signature:** `rest_json(path, token="", method="GET", params=None, body=None, accept="", timeout=20, retries=2, max_sleep_seconds=30) -> dict`.
**Data Shape:** Success ⇒ `{"data": <JSON or {}>, "status": <2xx-3xx>, "rate_limit": {"limit","remaining","reset" from X-RateLimit-* headers}}`. Terminal ⇒ `GitHubAPIError(message, status, details=<parsed error JSON>)`.

### Decisive source
```python
can_retry = attempt < retries
if can_retry and status in (429, 500, 502, 503, 504):          # :251
    sleep_seconds = min(max_sleep_seconds, 2 ** attempt)        # exp backoff, cap 30s
    time.sleep(max(1, sleep_seconds)); attempt += 1; continue

if can_retry and status == 403 and remaining == "0" and reset:  # rate-limit class :257
    reset_ts = int(reset)
    wait_for = max(1, min(max_sleep_seconds, reset_ts - int(time.time()) + 1))
    time.sleep(wait_for); attempt += 1; continue

message = payload_json.get("message", f"GitHub API error: HTTP {status}")
raise GitHubAPIError(message=message, status=status, details=payload_json)
```

**Flow:** build URL (`_build_url`, params urlencoded) → POST body JSON-encoded once outside the loop → `safe_request` (SSRF-guarded, TLS forced) → status<400: parse JSON (empty body ⇒ `{}`), return envelope with `X-RateLimit-*` headers → 429/5xx: capped exponential sleep `min(30, 2^attempt)` → 403 with `X-RateLimit-Remaining == "0"` AND a reset epoch: sleep exactly until reset (+1s), clamped to the same cap → anything else (or retries spent): raise `GitHubAPIError` carrying GitHub's own `message` + parsed body as `details` → non-GitHub exceptions retried with identical backoff, then wrapped as `"Network error while calling GitHub API: …"`; loop exit ⇒ `"GitHub API request retries exhausted."`.
**Invariant:** The two wait policies must stay separate — resetting on a *rate-limit* 403 by exponential backoff wastes the window (reset may be minutes away) while treating ordinary 403s (forbidden, not exhausted) as retryable would hang. `remaining == "0"` string compare is deliberate: the header is text.
**Probe:** executed grep pins on `scripts/github_api.py`: `status in \(429, 500, 502, 503, 504\)` = 1 (:251), `min\(max_sleep_seconds, 2 \*\* attempt\)` = 1 (:252), `remaining == "0"` = 1 (:257); repo-owned suite 34 passed @pin.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"rest_json retries exhausted rate limit reset GitHubAPIError","limit":5}}
```
Executed live: resolves `scripts/github_api.py:rest_json` (:197-278) rank-2 (behind an unrelated pagespeed test) plus `GitHubAPIError`/`__init__`.

## Verdict
Adopt the dual-ladder (status-set backoff vs reset-aware 403) and the `{data,status,rate_limit}` envelope verbatim for metered REST APIs; adapt `max_sleep_seconds=30`/`retries=2` to host latency budget; omit GraphQL-over-REST reuse only if your host has a native endpoint (here `graphql_json` posts `/graphql` through this same ladder and re-raises on payload `errors`). Coverage caveat: no direct upstream unit test drives this function; evidence is executed content pins + byte-identical snippet/direct read at pin.
