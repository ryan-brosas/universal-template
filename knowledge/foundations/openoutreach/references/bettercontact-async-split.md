<!-- capsule-v2 -->
# BetterContact async transport split — one client, two blocking contracts, refusals typed once

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** How do you share one provider transport between a caller that must block (discovery) and one that must never block (enrichment), while keeping 401/402/429 semantics distinct?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/enrichment/bettercontact.py:submit` (:175-190), `poll_once` (:193-219), `submit_and_poll` (:248-265), `_request` (:281-308), `_RETRY` (:62-70).
**Signature:** `submit(query) -> str (request_id)`; `poll_once(request_id) -> PollOutcome{running, email, first_name, last_name}`; `submit_and_poll(api_key, url, body) -> dict`.
**Data Shape:** `PollOutcome.hit = not running and bool(email)`; `.miss = not running and not email`. Provider row fields: `contact_email_address`, `contact_email_address_status ∈ {valid, deliverable, catch_all_safe}` (`_USABLE_STATUSES`).

### Decisive source
```python
_RETRY = Retry(total=5, status_forcelist=(429,), allowed_methods=frozenset({"GET","POST"}),
               backoff_factor=5, backoff_max=120, respect_retry_after_header=True,
               raise_on_status=True)
# only 429 is retried — a 401 or a 402 is a final answer, and repeating it would be noise

def _request(self, session, method, url, **kwargs):
    try:
        resp = session.request(method, url, timeout=_HTTP_TIMEOUT_S, **kwargs)
    except requests.exceptions.RetryError as exc:      # adapter exhausted its 429 backoff
        raise BetterContactUnavailable("...rate-limited this client through "
            f"{_RATE_LIMIT_ATTEMPTS} backed-off attempts", ErrorType.PROVIDER_RATE_LIMITED) from exc
    if resp.status_code == 401:
        raise BetterContactUnavailable("...rejected the API key (401)", ErrorType.PROVIDER_AUTH)
    if resp.status_code == 402:
        raise BetterContactUnavailable("...credits are exhausted (402)", ErrorType.PROVIDER_OUT_OF_CREDITS)
```

**Flow:** enrichment calls `submit` (returns request_id immediately) and later `poll_once` (one GET, no wait); discovery legitimately waits inside `submit_and_poll` (5s interval, 300s deadline). Both share `_session` (browser UA — Cloudflare 403s non-browser agents with error 1010 — plus X-API-Key and the urllib3 Retry adapter).
**Invariant:** The 429 backoff lives in the transport adapter, never in hand-rolled loops ("a worse copy of urllib3"), because their docs warn that firing through a 429 can get the whole *account* blocked. Every failure raises `BetterContactUnavailable` with a stable `error_type` — never a bare error, never an empty-page-as-success — so callers can distinguish refused-key / empty-wallet / rate-limited / unreachable without matching on messages. An empty submit response (no request_id) is also `BetterContactUnavailable`.
**Probe:** `tests/test_bettercontact.py::TestSubmit` (:84-113), `TestPollOnce` (:114-172), `TestIsConfigured` (:177+), `TestSignupUrl` (:185+).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "poll_once", limit: 5 });
```

## Verdict
Adopt the submit/poll_once vs submit_and_poll split keyed on which caller may block; adopt Retry(status_forcelist=(429,), respect_retry_after_header=True) + typed refusals at the HTTP boundary; adopt usable-status allow-listing before trusting a returned email. Adapt endpoints/keys to your provider; omit the signup-attribution constant (SIGNUP_URL path-only-by-design — affiliate parameter applied at the redirect so terminals can't strip it at the `?`).
