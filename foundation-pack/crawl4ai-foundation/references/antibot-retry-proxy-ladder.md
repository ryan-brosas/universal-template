<!-- capsule-v2 -->

# Anti-bot retry x proxy ladder with fallback fetch — What is the exact retry topology when a fetch comes back blocked, and when does an exception propagate versus get swallowed?

**Source:** crawl4ai Apache-2.0 `main@7e801521428ee12509994d39151006f64055ebe3`; Codebase Memory `ext-crawl4ai`. **Question:** What is the exact retry topology when a fetch comes back blocked, and when does an exception propagate versus get swallowed?

## Nested attempt/proxy loops inside arun

**Path/Symbol:** `crawl4ai/async_webcrawler.py:AsyncWebCrawler.arun (399-646)`.

**Signature:** `_max_attempts = 1 + getattr(config, "max_retries", 0); _proxy_list = config._get_proxy_list()`.

**Data Shape:** `_crawl_stats` dict accumulates attempts/retries/proxies_used[{proxy,status_code,blocked,reason}]/fallback_fetch_used/resolved_by ('direct'|'proxy'|'fallback_fetch') and is attached to EVERY returned CrawlResult as `.crawl_stats`.

### Decisive source
```python
for _attempt in range(_max_attempts):
                        ...
                        for _p_idx, _proxy in enumerate(_proxy_list):
                            config.proxy_config = _proxy
                            try:
                                ...
                                crawl_result.success = bool(html) or bool(async_response.downloaded_files)
                                ...
                                if not _blocked:
                                    _done = True
                                    break  # Success — exit proxy loop
                            except Exception as _crawl_err:
                                ...
                                # If this is the only proxy and only attempt, re-raise
                                # so the caller gets the real error (not a silent swallow).
                                if len(_proxy_list) <= 1 and _max_attempts <= 1:
                                    raise
                    # Restore original proxy_config
                    config.proxy_config = _original_proxy_config
```

**Flow:** robots.txt gate first (returns 403 CrawlResult, once, before any attempt) -> raw: URLs skip blocking/retries/fallback entirely (caller-provided HTML) -> attempt loop x proxy loop: each iteration sets config.proxy_config, crawls, processes, marks blocked via is_blocked -> break on first clean fetch -> after loops: restore original proxy -> optional caller `fallback_fetch_function` invoked when (result is None OR still blocked) and not raw: -> its failure path degrades to a minimal success=True CrawlResult carrying raw HTML when aprocess_html itself dies (dead browser) -> final block re-check SKIPPED only when fallback succeeded / raw / binary download (PerimeterX markers in real pages cause false positives) else failed result with error_message -> no result at all -> minimal 'All proxies failed' CrawlResult so callers always receive crawl_stats.

**Invariant:** (1) Success is `bool(html) or bool(downloaded_files)` - PDFs/archives legitimately have empty html; treating empty-html-as-failure breaks binary downloads. (2) Exceptions propagate ONLY from the single-attempt-single-proxy case; otherwise they become another proxies_used entry and the loop continues. (3) The final is_blocked re-check runs even after a BLOCKED last attempt - skipping it when fallback merely ran (not succeeded) would ship garbage as success.

**Probe:** `tests/proxy/test_antibot_detector.py` + `tests/proxy/test_sticky_sessions.py` (sticky session feeds the same proxy into this ladder; crawl_stats fields pinned indirectly via integration tests)

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph '{"project": "ext-crawl4ai", "query": "arun anti-bot retry proxy loop", "limit": 5}'
```

## Verdict
Adopt the loop shape: outer retries x inner proxies, success = non-empty html OR downloaded_files, exception swallowed while more candidates remain but re-raised when it was the ONLY attempt, original proxy restored in all cases, stats dict attached to every terminal result including the all-failed minimal result. Adapt attempt counts and the fallback function itself (host-specific transport). Omit crawl4ai's specific logger tags freely.
