<!-- capsule-v2 -->
# Exception taxonomy wiring — how do I shape a scraper's error hierarchy so callers route failures without string-matching, and where does the taxonomy lie to you?

**Source:** linkedin_scraper GPL-3 `master@b1cdc1c0e85bee8764d62565d229c682e5eb81bb` (≡ joeyism-linkedin-scraper identical tree); Codebase Memory `linkedin_scraper`. **Question:** which subsystem raises which typed exception, what machine-actionable payload rides on it, and which documented errors are never actually raised?

## The 7-class hierarchy and its real raise sites
**Path/Symbol:** `linkedin_scraper/core/exceptions.py` (:1–39 — LinkedInScraperException base; AuthenticationError; RateLimitError(message, suggested_wait_time=300); ElementNotFoundError; ProfileNotFoundError; NetworkError; ScrapingError). Raise-site map at this pin: core/auth.py raises AuthenticationError at :92/:115/:138/:148/:157/:181/:188 (credentials ladder), :218/:242 (cookie path), :309 (manual-login window); core/utils.py detect_rate_limit raises RateLimitError at :72/:82 (checkpoint+CAPTCHA → suggested_wait_time=3600) and :100 (body-text messages → 1800), wait_for_element_smart raises ElementNotFoundError :134 with selector suggestions; core/browser.py start() wraps launch failure as NetworkError :88 and guards uninitialized access with plain RuntimeError :122–:225 + FileNotFoundError :191; scrapers/person.py scrape() re-wraps ANY failure as ScrapingError :110.
**Signature:** `RateLimitError(message: str, suggested_wait_time: int = 300)` stores the wait as an attribute (`self.suggested_wait_time`) while passing message to super().
**Data Shape:** one root class lets callers catch "any scraper failure"; leaf classes encode WHO failed (auth / throttle / DOM-miss / transport / orchestration); exactly ONE class carries a scheduler-consumable numeric payload.

### Decisive source
```python
class RateLimitError(LinkedInScraperException):
    def __init__(self, message: str, suggested_wait_time: int = 300):
        super().__init__(message)
        self.suggested_wait_time = suggested_wait_time   # tiered at raise sites:
#   checkpoint/authwall URL or CAPTCHA iframe -> 3600 (1 hour)
#   body text 'too many requests'/'rate limit'/'slow down' -> 1800
#   constructor default 300 for callers that raise without measuring
```

**Flow:** auth failures surface ONLY as AuthenticationError from every login path (credentials, cookie, manual-login poll) → throttling surfaces ONLY as RateLimitError from detect_rate_limit, which BaseScraper.check_rate_limit calls after every navigation → browser-start failures become NetworkError while later lifecycle misuse stays RuntimeError (not part of the taxonomy — deliberate: misuse is a programming error, not an operational state) → person.scrape is the ONLY orchestrator that converts everything beneath it into ScrapingError.
**Invariant:** catch order matters — `except RateLimitError` before `except LinkedInScraperException`, since every leaf subclasses the root; the suggested_wait_time contract means schedulers read the ATTRIBUTE, never parse message text; detect_rate_limit's body-text probe must swallow PlaywrightTimeoutError (:104) so "page too slow to probe" can never masquerade as "throttled".
**Probe:** executed at this pin: `RateLimitError("m", suggested_wait_time=1800).suggested_wait_time == 1800`; default instance == 300; `isinstance(e, LinkedInScraperException)` true. TRAP recorded: JobScraper.scrape/CompanyScraper.scrape docstrings promise `ProfileNotFoundError ... if job posting not found`, but NO code in the package raises ProfileNotFoundError — a 404 job page currently degrades to all-None fields instead of raising. Porters must not rely on that documented contract.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin_scraper", file_pattern: "core/exceptions.py", format: "tree", limit: 20 });
```

## Verdict
Adopt: single-root taxonomy, per-subsystem leaf classes, numeric scheduler payload on the throttle error with TIERED values chosen by signal severity (hard challenge > soft warning), keep misuse errors OUTSIDE the hierarchy. Adapt tier durations and signal probes per host. Omit nothing silently: if your docstrings promise an error class, wire it — this repo shows the cost (ProfileNotFoundError is dead documentation). Coverage caveat: exceptions.py itself has no direct unit test; evidence is whole-file source read + repo-wide grep of raise sites at the cited pin.
