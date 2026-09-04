<!-- capsule-v2 -->
# fetch envelope — how do you give 38 CLI scripts a fetcher that never raises?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `aeo-agentic-seo-skill`. **Question:** What result-dict contract does the shared `fetch_url` return on success AND failure, and how does it sit on top of the SSRF-safe primitive?

## Non-raising fetch dict over safe_request
**Path/Symbol:** `scripts/seo_common.py:fetch_url` (:90-138), `load_html` (:159-165), `read_urls` (:141-156). Wraps `safe_request` from `lib/safe_http` (see `safe-http-ssrf-guard` capsule) via dual-path import (:26-29). Fan-in at pin: 38 call sites across scripts/.
**Signature:** `fetch_url(url: str, method: str = "GET", timeout: int = 15, allow_redirects: bool = True, max_bytes: int = 2_000_000, extra_headers: dict | None = None) -> dict`.
**Data Shape:** Always returns one dict with keys `input_url, url, status, headers, text, bytes, redirect_chain, error` — initialized to `None/{}/""/0/[]/None` before any I/O. Success fills `url` (FINAL post-redirect), `status`, lowercased-key `headers`, `redirect_chain` (list of intermediate URLs), and — only when method ≠ HEAD — `bytes`/`text`. Failure leaves `error` set (`str(exc)` or scheme message) with every other field at its sentinel; no exception ever escapes.

### Decisive source
```python
if parsed.scheme not in ("http", "https"):
    result["error"] = f"Unsupported URL scheme: {parsed.scheme}"   # :112
    return result
...
result["headers"] = {str(k).lower(): v for k, v in response.headers.items()}  # :130
result["redirect_chain"] = [r.url for r in response.history]      # :131
if method.upper() != "HEAD":                                      # :133
    result["bytes"] = len(response.content)
    result["text"] = response.text
except requests.exceptions.RequestException as exc:
    result["error"] = str(exc)                                    # :137
```

**Flow:** `require_requests()` guard (exit 1 with pip hint if optional dep missing) → `normalize_url` (default-scheme https, fragment stripped) → scheme gate rejects non-http(s) as a RESULT, not an exception → headers default to a browser-ish `Accept`, `extra_headers` merged AFTER so callers can override → delegate to `safe_request(method, url, headers, timeout, allow_redirects, max_response_bytes=max_bytes)` — all SSRF revalidation lives there, this layer adds none → copy final URL/status/lowercased headers/history → body fields only for non-HEAD → any `RequestException` becomes `error=str(exc)`.
**Invariant:** Callers branch on `result["error"] is None` / `result["status"]`, never on try/except — that is why 38 scripts can share it without per-call error plumbing. Header keys are ALWAYS lowercase at this layer (consumers must not re-lowercase). `input_url` vs `url` distinguishes what was asked from where it landed; dropping either breaks redirect-chain audits. HEAD responses must not populate `text`/`bytes` (requests would raise on `.content` for some HEAD paths — the guard makes the envelope total).
**Probe:** no direct upstream test for `fetch_url`/`load_html`/`read_urls`; content pins executed at pin: `max_bytes: int = 2_000_000` :95 ×1, `Unsupported URL scheme` :112 ×1, `str(k).lower()` :130 ×1, `r.url for r in response.history` :131 ×1, `method.upper() != "HEAD"` :133 ×1, `result["error"] = str(exc)` :137 ×1, load_html heuristic `re.match(r"^https?://"` :160 ×1; full suite 34 passed. Companion heuristic worth porting with the envelope: `load_html` treats a source as a URL iff it matches `^https?://` OR contains `.` without `/` (:160) — otherwise it is read as a local file, which is what lets every checker accept both a path and a link.
**Retrieve:**
```json
{"tool":"mcp__codebase-memory__search_graph","args":{"project":"aeo-agentic-seo-skill","query":"fetch_url safe_request redirect chain error envelope","limit":5}}
```
Not executed this pass — Codebase Memory MCP surface absent in the pass-3 session; seam selected and confirmed by direct full-file read of seo_common.py (396L) at pin (recorded in verification.md). Execute on revalidation.

## Verdict
Adopt the total-result-dict pattern verbatim for any shared fetch helper feeding many independent checkers — the sentinel-initialized dict plus single `error` string is the whole contract. Adapt the byte cap (2 MB default), timeout, and Accept header to your host policy; keep the SSRF revalidation in the lower layer (safe_http) and do NOT duplicate it here. Omit nothing structural. Coverage caveat: network behavior is content-pinned only — no upstream test drives fetch_url against a live or mocked socket.
