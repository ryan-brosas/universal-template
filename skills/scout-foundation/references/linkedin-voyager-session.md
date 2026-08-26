<!-- capsule-v2 -->
# LinkedIn Voyager session — how does a li_at cookie become an authenticated API client with CSRF, and how does it survive across scrapes?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How is the cookie→session→CSRF chain built once and invalidated on expiry, and which response envelope field holds the profile?

## Cookie-jar CSRF harvest + module-global session cache + 401 self-invalidation
**Path/Symbol:** `app/scrapers/linkedin.py:_get_li_cookie` (:18-24), `_get_session` (:48-73), `scrape_linkedin_profile` (:76-158).
**Signature:** `_get_session() -> tuple[httpx.Client, str] | (None, None)`; cache `_session_cache = {'client': None, 'csrf': None}`.
**Data Shape:** endpoint `GET www.linkedin.com/voyager/api/identity/dash/profiles?q=memberIdentity&memberIdentity=<user>`; headers: `csrf-token`, `Accept: application/vnd.linkedin.normalized+json+2.1`, `x-restli-protocol-version: 2.0.0`.

### Decisive source
```python
client.cookies.set('li_at', cookie, domain='.linkedin.com')
client.get('https://www.linkedin.com/feed/')          # bootstrap visit mints JSESSIONID
for c in client.cookies.jar:
    if c.name == 'JSESSIONID':
        csrf = c.value.strip('"')                     # token arrives QUOTED
        break
...
if resp.status_code == 401:
    _session_cache.update({'client': None, 'csrf': None})   # poisoned cache ⇒ rebuild
    return None
...
profile_data = next(item for item in data.get('included', [])
                    if 'firstName' in item and 'lastName' in item)
```

**Flow:** validate-shaped cookie (`len < 50` warns) → one `/feed/` GET with the li_at cookie → harvest JSESSIONID from the response cookie jar, strip surrounding quotes → cache client+csrf for all subsequent profiles in the batch → per-profile Voyager GET; 403=restricted (per-profile skip), **401=expired ⇒ wipe the cached session so the NEXT profile rebuilds it**, other codes log-and-None. Profile fields come from the first `included[]` entry carrying both names (the normalized JSON envelope), with `multiLocaleSummary.en_US` fallback for summary and `websites[].url` for the site.
**Invariant:** the session cache is a liability as much as an asset — if the cookie expires mid-batch, a stale cached client would 401 forever unless the 401 branch nulls it; this self-healing invalidation is the piece porters forget. The CSRF value MUST be unquoted or Voyager rejects it. The orchestrator's pre-check (`LINKEDIN_COOKIE` gate before collecting usernames) exists because every profile would otherwise fail one-by-one.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "JSESSIONID\|_session_cache" app/scrapers/linkedin.py` pins :62-72/:109; graph retrieval resolves `Scout.app.scrapers.linkedin.scrape_linkedin_profile`.
**Coverage caveat:** pinned by source only; `validate_cookie()` (:27-45) is dead upstream (no callers) — its feed-redirect/authwall URL sniff documents intended validity semantics but is not wired.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "voyager csrf JSESSIONID linkedin", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt cookie→bootstrap→jar-harvest→cache→401-self-invalidate for any cookie-authenticated scraping session; adapt endpoints/headers to your target; omit Voyager specifics when LinkedIn's schema moves (re-pin against live responses). Port the quoted-JSESSIONID strip and included[]-envelope walk verbatim.
