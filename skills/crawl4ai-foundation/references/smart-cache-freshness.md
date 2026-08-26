<!-- capsule-v2 -->

# Smart-cache freshness validation (conditional requests + head fingerprint) — Can you reuse a cached crawl without re-rendering the page in a browser, and what happens when the freshness check itself fails?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** Can you reuse a cached crawl without re-rendering the page in a browser, and what happens when the freshness check itself fails?

## Four-state validator

**Path/Symbol:** `crawl4ai/cache_validator.py:CacheValidator.validate (83-201)`.

**Signature:** `async def validate(self, url, stored_etag=None, stored_last_modified=None, stored_head_fingerprint=None) -> ValidationResult(status: CacheValidationResult, new_etag, new_last_modified, new_head_fingerprint, reason)`.

**Data Shape:** CacheValidationResult in {FRESH, STALE, UNKNOWN, ERROR}. httpx client http2+follow_redirects; `_fetch_head` streams GET with Accept-Encoding identity, stops at </head> or 64KB.

### Decisive source
```python
if headers:
                response = await client.head(url, headers=headers)
                if response.status_code == 304:
                    return ValidationResult(status=CacheValidationResult.FRESH,
                                            reason="Server returned 304 Not Modified")
                ...
                if stored_head_fingerprint:
                    head_html, _, _ = await self._fetch_head(url)
                    if head_html:
                        new_fingerprint = compute_head_fingerprint(head_html)
                        if new_fingerprint and new_fingerprint == stored_head_fingerprint:
                            return ValidationResult(..., status=CacheValidationResult.FRESH, ...)
        except httpx.TimeoutException:
            return ValidationResult(status=CacheValidationResult.ERROR,
                                    reason="Validation request timed out")
```

**Flow:** If-None-Match/If-Modified-Since HEAD -> 304 means FRESH -> 200 means compare streamed-head fingerprint (match=FRESH w/ header refresh, diff=STALE, unfetchable=STALE-by-header-change) -> no conditional headers stored means fingerprint-only path -> nothing stored means UNKNOWN. Every network exception maps to ERROR, never raises. Caller wiring in arun: FRESH->cache_status='hit_validated'+persist new etag/last_modified/fingerprint; ERROR->cache_status='hit_fallback' (serve stale!); STALE|UNKNOWN->`cached_result = None` forcing full recrawl.

**Invariant:** Fingerprint inputs are fixed at utils.compute_head_fingerprint (:2847): lowercase head, extract <title>, meta[name=description], meta[name=last-modified], og:title/og:description/og:image/og:updated_time, article:modified_time (TWO attribute-order regexes per tag), join with '|', xxhash.xxh64 hexdigest; NO signals found means '' which never validates fresh. Crawl side stores it by slicing html at lower().find('</head>')+7 (async_webcrawler.arun ~:649).

**Probe:** `tests/cache_validation/test_head_fingerprint.py` (fingerprint stability across attribute orders; end-to-end in tests/cache_validation/test_end_to_end.py)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "CacheValidator validate head fingerprint", "limit": 5}'
```

## Verdict
Adopt the four-state validation mapping (FRESH->hit_validated+metadata refresh, ERROR->hit_fallback serve stale, STALE/UNKNOWN->drop cache and recrawl) and the xxhash signal-join fingerprint format exactly - a porter changing the signal list invalidates every persisted fingerprint. Adapt timeouts and the UA string. Omit nothing in the ERROR branch: failing OPEN to cache is the feature.
