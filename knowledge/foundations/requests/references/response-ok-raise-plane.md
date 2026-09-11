<!-- capsule-v2 -->
# ok / raise_for_status — which status codes raise, and what does truthiness mean on a Response?

**Source:** psf/requests Apache-2.0 `main@8f8b212de8c2129d7954c6cd373762880375620a`; Codebase Memory `requests`. **Question:** Exactly which statuses make `raise_for_status()` raise and `bool(response)` falsy — and how are non-UTF-8 reason bytes handled in the message?

## Response.raise_for_status / ok / __bool__
**Path/Symbol:** `src/requests/models.py:Response.raise_for_status` (:1144-1171), `.ok` (:861-874), `.__bool__` (:837-845), `.__nonzero__` (:847-855).
**Signature:** `raise_for_status() -> None`; `ok -> bool` property.
**Data Shape:** reads `status_code`, `reason` (bytes | str | None), `url`; failure output is a single `HTTPError(http_error_msg, response=self)`.

### Decisive source
```python
if isinstance(self.reason, bytes):
    try:
        reason = self.reason.decode("utf-8")     # localized reasons: try utf-8
    except UnicodeDecodeError:
        reason = self.reason.decode("iso-8859-1")  # never-failing fallback
else:
    reason = self.reason

if 400 <= self.status_code < 500:
    http_error_msg = f"{self.status_code} Client Error: {reason} for url: {self.url}"
elif 500 <= self.status_code < 600:
    http_error_msg = f"{self.status_code} Server Error: {reason} for url: {self.url}"

if http_error_msg:
    raise HTTPError(http_error_msg, response=self)

# .ok — the only internal caller (graph trace):
try:
    self.raise_for_status()
except HTTPError:
    return False
return True
```

**Flow:** reason bytes decoded utf-8→iso-8859-1 → error message built ONLY inside [400,500) or [500,600) → non-empty message raises HTTPError carrying the response → `.ok` reuses raise_for_status as its predicate by swallowing HTTPError; `__bool__` delegates to `.ok`.
**Invariant:** The windows are EXACTLY 4xx/5xx — a 3xx (even 304) and any code ≥600 or ≤399 NEVER raises, so `bool(response)` is not "is 2xx" but "not 4xx/5xx". The exception always carries `response=self`, which is what exceptions-hierarchy-context's back-fill relies on.
**Probe:** Direct test: `tests/test_requests.py::test_status_raising` (:934-940) pins HTTPError on a 404 via `raise_for_status()` AND `assert not r.ok` on a 500.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "requests", query: "raise_for_status HTTPError ok", limit: 10 });
```

## Verdict
Adopt the exact 4xx/5xx windows, response attachment, and bytes-reason decode ladder. Adapt message wording freely. Omit the py2 `__nonzero__` alias.
