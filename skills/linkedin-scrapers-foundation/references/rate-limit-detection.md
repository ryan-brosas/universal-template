<!-- capsule-v2 -->
# Rate-limit detection & backoff — how do I notice LinkedIn is throttling me and retry without making it worse?

**Source:** joeyism-linkedin-scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb`; cross-confirmed in open-linkedin-api (MIT) `default_evade` and Auto_job_applier_linkedIn (MIT) `buffer`. Codebase Memory `joeyism-linkedin-scraper`. **Question:** which page signals mean "back off", and how should retries be spaced so they don't deepen the throttle?

## detect_rate_limit + retry_async decorator
**Path/Symbol:** `linkedin_scraper/core/utils.py:detect_rate_limit` (:57–105), `retry_async` (:16–54); contrast `open_linkedin_api/linkedin.py:default_evade` (:29–34); contrast `Auto_job_applier_linkedIn/modules/helpers.py:buffer` (:143–159).
**Signature:** `async detect_rate_limit(page) -> None` (raises `RateLimitError(msg, suggested_wait_time=...)`); `retry_async(max_attempts=3, backoff=2.0, exceptions=(Exception,))` decorator; `buffer(speed)` sleeps `randint(lo,hi)*0.1` s by tier.
**Data Shape:** three signal classes — URL (`/checkpoint`, `authwall` → 3600 s), CAPTCHA iframe (`iframe[title*="captcha" i], iframe[src*="captcha" i]` → 3600 s), body-text phrases (`too many requests|rate limit|slow down|try again later` → 1800 s).

### Decisive source
```python
if 'linkedin.com/checkpoint' in current_url or 'authwall' in current_url:
    raise RateLimitError("...security checkpoint...", suggested_wait_time=3600)
...
wait_time = backoff ** attempt          # exponential: 1s, 2s, 4s for backoff=2.0
await asyncio.sleep(wait_time)
# after the final attempt: raise last_exception   — never swallow

# Auto_job_applier's tiered human-jitter alternative:
def buffer(speed=0):
    if speed <= 0: return
    elif speed <= 1: return sleep(randint(6,10)*0.1)      # 0.6–1.0 s
    elif speed <= 2: return sleep(randint(10,18)*0.1)     # 1.0–1.8 s
    else: return sleep(randint(18,round(speed)*10)*0.1)
```

**Flow:** every navigation (`BaseScraper.navigate_and_wait`) ends with `check_rate_limit()` → signals checked URL-first, then CAPTCHA iframes, then body phrases → raise with a suggested wait; transient `PlaywrightTimeoutError`s instead flow into `@retry_async` exponential-backoff wrappers (`safe_click` :121).
**Invariant:** rate-limit signals RAISE (stop the run, surface wait time); only timeout-class errors RETRY — conflating them makes throttling permanent. Detection failures are swallowed (`except Exception: pass` per probe) so a slow body-text read can't false-positive.
**Probe:** repo tests cover the auth side only (`tests/test_auth.py::test_is_logged_in_false`); no direct unit test pins detect_rate_limit — coverage caveat recorded; behavior verified by reading utils.py at HEAD.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "joeyism-linkedin-scraper", query: "detect_rate_limit", limit: 10 });
// resolves detect_rate_limit, retry_async, RateLimitError call sites in scrapers/base.py
```

## Verdict
Adopt the three-signal taxonomy with suggested-wait payloads and retry-only-timeouts discipline; adapt thresholds, phrase lists, and jitter tiers to host; omit selenium-stealth coupling. Cross-repo note: request-level pacing exists on a spectrum — fixed random sleep (voyager), tiered buffer (auto-job), post-hoc detection (joeyism) — pick per threat model.
