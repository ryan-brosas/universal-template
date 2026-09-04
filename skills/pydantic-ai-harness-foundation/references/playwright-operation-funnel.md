<!-- capsule-v2 -->
# Browser operation funnel: countdown deadlines, event-log span attribution, credential redaction at the chokepoint

## Source / Question
`pydantic_ai_harness/playwright/_toolset.py:312–360, 815–940, 1087–1120, 1555–1909` @ `main@f971198` — Eighteen tools share one page and one lock. How do you budget timeouts across multi-stage operations, attribute async page events to the right OTel span, keep page-controlled strings bounded, and guarantee no URL credential ever reaches model or trace?

## Path / Symbol
`playwright/_toolset.py` — `_Deadlines` frozen dataclass (:312–360), `_truncate` (:815–822), `BrowserEvent` + describe/attributes (:918–975), `_EVENT_LOG_LIMIT=500`/`_MAX_EVENT_CHARS=2000` (:893–907), `session.record/failure_since_operation_start/events_recorded+operation_events_mark/operation_span` (:1071–1120), toolset `_in_operation/_refuse/_error/_playwright_error/_await_with_timeout` (:1810–1899), `_without_credentials` + `_CREDENTIAL_PARAMETERS` + `_USERINFO` regex (:729–812).

## Signature
```python
@dataclass(frozen=True)
class _Deadlines:
    action_ms: int; navigation_ms: int; started: float     # 5s / 60s defaults, split ON PURPOSE
    @property
    def action(self) -> int: return self._remaining(self.action_ms)
    def _remaining(self, budget_ms: int) -> int:
        if budget_ms == 0: return 0                        # 0 IS "no deadline" — never let countdown reach it
        return max(1, budget_ms - int((monotonic()-self.started)*1000))
```

## Data Shape
Browser events: ring buffer (500) of clipped (2000 chars) records with kind/level/message/url/method/status; `events_recorded` is the STABLE counter that lets an operation ask only about events its own action caused (`caused_here = events_recorded - operation_events_mark`). Span events use OTel HTTP semconv names (`url.full`, `http.request.method`, `http.response.status_code`) so backends read them without custom mapping.

### Decisive source
Deadline ownership (:320–334): one call makes SEVERAL Playwright calls; handing each stage the whole number lets `navigate(timeout_ms=2000)` spend 2s five times. After a completed settle — and in navigate, after goto — everything runs on `navigation` because the action budget "is long gone by then". Per-call override collapses both budgets into one (:1735–1744); `timeout_ms<=0` refused per-call but kept as developer default (:1757–1767): "an injected page could otherwise ask for an unbounded call." Redaction chokepoint (:1087–1100): EVERY event passes through `record()`, which clips AND strips userinfo + credential-param values (`token=`, `client_secret`, `sig`, cloud signature params — full names listed because anchoring means `secret` ≠ `client_secret`) from url AND message ("a page that logs its own request reaches the model and the exporter through exactly the same two methods"). Regex-based so a URL Chromium accepted but urlsplit rejects is still cleaned (:783–786). CDP attach failures get endpoint stripped to scheme://host:port (:792–812). Tools return failures as bounded strings and set `browser.outcome=error` on the span themselves (:1678–1688) "so a span that took its outcome from whether an exception escaped would report every one of them as a success."

**Flow:** acquire operation lock → validate timeout → start span (`browser.action`, reported CONFIGURED budget not countdown) → publish `operation_span` + mark `operation_events_mark` → ensure_page INSIDE guarded region (launch failures are model-actionable results) → body → map PlaywrightError/TargetClosed/BrowserUnavailable to bounded strings → finally: stamp `url.full` (sanitized), clear span pointer.
**Invariant:** no page-controlled string enters output or telemetry unclipped/unredacted; guard-own aborts are recorded once (matching `net::ERR_FAILED` requestfailed events dropped, :886–891/:1148–1160); TargetClosedError with zero pages keeps the dead active pointer rather than silently resetting a fresh browser ("which would drop the session's cookies and history without saying so", :1723–1728).

## Probe (direct test)
`tests/playwright/test_playwright.py` — `test_navigate_truncates_url_and_title_within_shared_budget` :949, `test_screenshot_over_size_limit_returns_error_not_image` :1110 (5MB provider image cap → bounded error not BinaryContent), `test_navigate_keeps_the_oversized_note_when_page_text_fills_the_budget` :1125 + `…_cannot_fit` :1138 (note-first budgeting), oversized-screenshot-on-navigate :1117, blocked-redirect cause attribution :1031/:1064, concurrent navigations each report their own state :982.

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern '_Deadlines _without_credentials record failure_since_operation_start _in_operation'
```

## Verdict
**Adopt** the shared-deadline countdown, mark-and-count event attribution, and single-chokepoint redaction for ANY multi-tool wrapper over a stateful resource. **Adapt** budget numbers. **Omit** screenshot-size cap only if your provider differs.
