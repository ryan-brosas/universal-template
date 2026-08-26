<!-- capsule-v2 -->
# Instagram HTML scrape — how do you get profile JSON without an API, login wall, or phantom profiles?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How does the no-login instagram scraper detect not-found/login-wall/rate-limit states that all return HTTP 200, and why must a real profile have followers?

## Mobile-UA fetch + signal-sniffing ladder + follower-count authenticity gate
**Path/Symbol:** `app/scrapers/instagram.py:scrape_profile_no_login` (:46-116), `_is_page_not_found` (:32-43), `_extract_profile_from_html` gate (:241-242).
**Signature:** `scrape_profile_no_login(username: str, max_retries: int = 3) -> Optional[Dict]`; raises `RuntimeError` ONLY on rate limit (see retry-semantics.md).
**Data Shape:** GET `instagram.com/<user>/` with MOBILE UA list (4 iPhone/Android strings — desktop UAs get the login wall); regex ladder over embedded JSON keys.

### Decisive source
```python
# three 200-OK failure modes, each with its own tell:
if _is_page_not_found(html):        # "Sorry, this page isn", '"HttpErrorPage"'
    return None                      # ...checked in FIRST 10,000 chars only
if '/accounts/login' in r.url or ('login' in html[:5000].lower()
                                  and 'password' in html[:5000].lower()):
    return None                      # soft login wall ⇒ treat as absent
...
# the authenticity gate — extracted-but-empty means you parsed a shell page:
if 'follower_count' not in results or results.get('follower_count', 0) == 0:
    return None

# unicode-escape bio decode with surrogate round-trip:
decoded = match.group(1).encode('utf-8').decode('unicode_escape')
results['biography'] = decoded.encode('utf-16', 'surrogatepass').decode('utf-16')
```

**Flow:** 3 attempts; per attempt fresh proxy draw + random mobile UA. 404→None; **429→RuntimeError (batch-fatal)**; other non-200/timeout → sleep(1) retry; 200 → not-found sniff → login-wall sniff → regex extract (username/full_name/bio/counts/verified/external_url; meta-description `X Followers, Y Following, Z Posts` fallback via abbreviated-number parse) → gate on positive follower_count → build standard profile.
**Invariant:** status codes alone cannot classify this endpoint — not-found and login-wall arrive as 200 with different bodies, so body sniffing is load-bearing. The follower-count-zero rejection is deliberate: every genuine profile has ≥1 follower, while bot-wall/interstitial pages sometimes yield parseable-looking zeros. The exotic UTF-8→UTF-16-surrogatepass round-trip exists because IG embeds `\uXXXX` escapes containing surrogate pairs that plain `unicode_escape` decoding mangles — porters who "simplify" it corrupt emoji bios.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "_is_page_not_found\|accounts/login\|follower_count.*== 0" app/scrapers/instagram.py` pins :80-84/:241-242; graph retrieval resolves `Scout.app.scrapers.instagram.scrape_profile_no_login`.
**Coverage caveat:** pinned by source only; live behavior drifts with IG markup.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "instagram login wall mobile user agent", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the 200-OK-state-classification ladder and the surrogate-safe escape decode for any embedded-JSON-in-HTML scraping; adapt signals per target site; omit the specific IG regex set when upstream changes keys (re-verify against live pages before trusting field coverage).
