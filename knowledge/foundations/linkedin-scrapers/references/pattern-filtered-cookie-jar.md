<!-- capsule-v2 -->
# Pattern-filtered cookie jar — how do you persist ONLY the session cookies you need and restore them without touching the rest?

**Source:** zendriver AGPL-3.0 — PATTERNS ONLY. `main@2c6d9c7d`; Codebase Memory `ext-zendriver`. **Question:** how do you save/load a browser's cookies with a regex filter so you persist just the auth cookies (e.g. `li_at`) and replay them into a fresh profile?

## Regex-matched pickle round-trip over the storage domain
**Path/Symbol:** `zendriver/core/browser.py:CookieJar` (:676-830), `Browser.cookies` (:169-173).
**Signature:** `CookieJar.get_all(requests_cookie_format=False)`; `set_all(cookies)`; `save(file=".session.dat", pattern=".*")`; `load(file, pattern=".*")`; `clear()`.
**Data Shape:** cookies come from `cdp.storage.get_cookies()` as `cdp.network.Cookie`; `requests_cookie_format=True` converts to `requests.cookies.create_cookie` objects (name/value/domain/path/expires/secure) for interop. `save`/`load` pickle the `Cookie.__dict__`-serializable list to a binary file.

### Decisive source
```python
compiled_pattern = re.compile(pattern)
for cookie in cookies:
    for match in compiled_pattern.finditer(str(cookie.__dict__)):
        included_cookies.append(cookie)   # ANY field (domain/key/value) matching pattern includes it
        break
with save_path.open("w+b") as save_file:
    pickle.dump(included_cookies, save_file)
# load: pickle.load → same pattern filter → await self.set_all(included_cookies)
```

**Flow:** `save` reads all cookies, keeps those where ANY serialized field matches the regex (e.g. `"(cf|.com|nowsecure)"` — domain OR key OR value), pickles to disk. `load` reads, re-filters, and `set_all` via `cdp.storage.set_cookies`. `clear` wipes via `cdp.storage.clear_cookies` (all tabs/windows). The connection is chosen from the first non-closed tab, falling back to the browser-level connection.
**Invariant:** the filter is a SUBSET selector, not a namespacer — a cookie is included if its `str(__dict__)` matches, so broad patterns like `".*"` capture everything and narrow ones like `"li_at"` capture just the session cookie. The pickle is the raw CDP cookie objects, so restore is byte-faithful (no re-parsing drift).
**Probe:** REAL tests — `tests/core/test_browser.py:117 test_cookies_save_writes_only_the_cookies_matching_the_pattern` (asserts only matching cookies persisted), `:141 test_cookies_save_and_load_round_trip`. Cross-reference: linkedin-scrapers' cookie-session-persistence (browser login ladder) and cookie-session-bootstrap (plant `li_at` per page) — zendriver is the generic jar; the LinkedIn suites are the concrete auth-cookie consumers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "CookieJar save load set_all pattern", limit: 5 });
```

## Verdict
Adopt: regex-subset cookie persistence with faithful pickle round-trip and requests-format interop. Adapt the file format if cross-language porting (pickle is Python-only). Omit the requests-format branch unless you interoperate with `requests`. Coverage: directly test-pinned (two live tests).
