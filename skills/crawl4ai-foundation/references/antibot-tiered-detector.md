<!-- capsule-v2 -->

# Anti-bot tiered detector — How do you decide a fetched page was blocked without false-positiving real content that mentions block-page phrases?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** How do you decide a fetched page was blocked without false-positiving real content that mentions block-page phrases?

## Layered verdict function

**Path/Symbol:** `crawl4ai/antibot_detector.py:is_blocked (191-281)`.

**Signature:** `def is_blocked(status_code: Optional[int], html: str, error_message: Optional[str] = None) -> Tuple[bool, str]`.

**Data Shape:** Returns (blocked: bool, reason: str) with reason='' when clean. Module constants carry the tuning: `_TIER2_MAX_SIZE=10000`, `_STRUCTURAL_MAX_SIZE=50000`, `_BLOCK_PAGE_MAX_SIZE=5000`, `_EMPTY_CONTENT_THRESHOLD=100`.

### Decisive source
```python
# --- HTTP 429 is always rate limiting ---
    if status_code == 429:
        return True, "HTTP 429 Too Many Requests"

    snippet = html[:15000]
    ...
    # Large-page deep scan: strip scripts/styles and re-check tier 1
    if html_len > 15000:
        _stripped_for_t1 = _SCRIPT_BLOCK_RE.sub('', html[:500000])
        _stripped_for_t1 = _STYLE_TAG_RE.sub('', _stripped_for_t1)
        _deep_snippet = _stripped_for_t1[:30000]
        ...
    if status_code in (403, 503) and not _looks_like_data(html):
        ...
        # Even without a pattern match, a non-data 403/503 HTML page is
        # almost certainly a block. Flag it so the fallback gets a chance.
        return True, f"HTTP {status_code} with HTML content ({html_len} bytes)"
```

**Flow:** docstring states the philosophy: 'false positives are cheap (the fallback mechanism rescues them), false negatives are catastrophic' -> Tier-1 vendor-structural regexes (Akamai Reference#, Cloudflare challenge-form/__cf_chl_f_tk_, cf-error-code spans, PerimeterX window._pxAppId, captcha-delivery.com, _Incapsula_Resource, KPSDK...) run against the first 15KB on ANY page, plus a scripts/styles-stripped re-scan of <=500KB->30KB for large SPA shells -> 429 always blocked -> 403/503 with non-data HTML ALWAYS blocked even when no pattern matches (modern block pages exceed 100KB) -> Tier-2 generic phrases (Access Denied, Just a moment, g-recaptcha...) gated to pages <10KB (or the stripped snippet on large 403/503) -> 200+near-empty (<100 bytes non-data) -> Tier-3 structural integrity.

**Invariant:** _looks_like_data (raw JSON/XML or `<pre>{`-wrapped) exempts a response from the status-code and structural checks - an API returning 403 JSON must NOT be flagged. Structural signals: no <body> = instant block; otherwise score minimal_text(<50 visible chars)/no_content_elements/script_heavy_shell - block at >=2 signals, or 1 signal when page <5000 bytes.

**Probe:** `tests/proxy/test_antibot_detector.py` (pins tier behavior incl. vendor patterns and data-response exemption)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "is_blocked anti-bot detection", "limit": 5}'
```

## Verdict
Adopt the tier ladder and its size gating verbatim - Tier-1 any size, Tier-2 <10KB, structural <50KB with the >=2-signals (or 1-signal-on-<5KB) rule, 429 unconditional, 403/503-with-HTML unconditional, data responses exempt everywhere. Adapt the pattern lists to targets you actually crawl (they are vendor snapshots, not contracts). Omit nothing structural: dropping the `_looks_like_data` exemptions reintroduces the false-positive class this design exists to prevent.
