<!-- capsule-v2 -->
# cookie-jar-storage-plane — persistence with regex subsetting, and why cookies go through `storage` not `network`

**Source:** zendriver MIT `main@2c6d9c7daaab543d34e9fe2b0ef7eaa171c79760`; Codebase Memory `ext-zendriver`. **Question:** How are all-profile cookies read/written and selectively saved/restored?

## CookieJar rides the first open tab, else the browser connection
**Path/Symbol:** `zendriver/core/browser.py:CookieJar` (:676-830) + `HTTPApi` (:833-863).
**Signature:** `async def get_all(self, requests_cookie_format: bool = False)`; `async def set_all(self, cookies: List[cdp.network.CookieParam])`; `async def save(self, file=".session.dat", pattern=".*")`; `async def load(self, file, pattern)`; `async def clear()`.
**Data Shape:** save format is a raw **pickle** of `cdp.network.Cookie` objects; `pattern` matches against `str(cookie.__dict__)` — i.e. domain, name, or value substrings via one regex.

### Decisive source
```python
connection: Connection | None = None
for tab_ in self._browser.tabs:
    if tab_.closed:
        continue
    connection = tab_
    break
else:
    connection = self._browser.connection
...
cookies = await connection.send(cdp.storage.get_cookies())
```
and the pattern filter (:762-771):
```python
for cookie in cookies:
    for match in compiled_pattern.finditer(str(cookie.__dict__)):
        included_cookies.append(cookie)
        break
```

**Flow:** every CookieJar op picks the first non-closed page tab (falls back to the browser-level connection) because `storage.get/set/clear_cookies` at browser scope covers the whole profile — unlike `network.getCookies` which is per-context. Save→pickle to disk; load→unpickle, re-filter with the same pattern, then `set_all`. `requests.cookies.create_cookie` converts to requests-compatible objects on demand.
**Invariant:** pickle load is unauthenticated deserialization of a user-created file (fine for local sessions, never expose); the `break` inside the match loop makes the filter first-match-per-cookie, so one hit suffices. A port that filters per-field instead of per-dict-repr changes what patterns can select.
**Probe:** direct tests pin save/load round-trip and pattern subsetting: `tests/core/test_browser.py::test_cookies_save_writes_only_the_cookies_matching_the_pattern` (:81+), `::test_cookies_save_and_load_round_trip`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zendriver", query: "CookieJar save load pickle", limit: 5 });
```

## Verdict
Adopt storage-domain cookie access and dict-repr pattern filtering; swap pickle for JSON if files cross trust boundaries; omit the requests-format shim when unused.
