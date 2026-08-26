<!-- capsule-v2 -->
# YouTube channel scrape — how do handle/channel-ID inputs, consent cookies, and redirect-wrapped links resolve into one profile?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How does one entry point accept @handles AND UC… IDs, dodge the EU consent wall, and recover real outbound URLs from google redirects?

## Identifier routing + CONSENT cookie + single-retry with fresh UA
**Path/Symbol:** `app/scrapers/youtube.py:scrape_channel` (:24-74), `_extract_channel_data` (:77-144), `_clean_redirect_url` (:151-158).
**Signature:** `scrape_channel(channel_identifier: str) -> Optional[Dict]`; routing: `@x`→`/x`, `UC…`(len 24)→`/channel/UC…`, else→auto-`@` prefix.
**Data Shape:** cookies: `{'CONSENT': 'PENDING+999'}`; extraction anchors: `"channelMetadataRenderer":{"title"`, `"subscriberCountText"` (simpleText OR accessibility-label variants), `"canonicalChannelUrl"`, `"channelId":"(UC[a-zA-Z0-9_-]{22})"`, `"businessEmailLabel":{"content"`.

### Decisive source
```python
cookies = {'CONSENT': 'PENDING+999'}       # pre-answer the EU consent dialog
...
result = _extract_channel_data(html, channel_identifier)
if result:
    return result
headers['User-Agent'] = random_user_agent()  # ONE full retry, new identity
r = requests.get(url, headers=headers, cookies=cookies, timeout=20, proxies=...)
if r.status_code == 200:
    return _extract_channel_data(r.text, channel_identifier)
return None

def _clean_redirect_url(url):               # unwrap youtube.com/redirect?q=
    if 'youtube.com/redirect' in url:
        q_match = re.search(r'[?&]q=([^&]+)', url)
        if q_match:
            from urllib.parse import unquote
            return unquote(q_match.group(1))
    return url
```

**Flow:** route identifier to canonical URL → GET with consent cookie → extract → on failure exactly one more attempt with a different random UA and fresh proxy draw. Extraction pulls name/description/subscribers (abbreviated-parse)/handle/channel-id; business email comes from the `businessEmailLabel` render node when present, ELSE regex-sniffed from the description. Outbound links come only from `"urlEndpoint":{"url":"…"}` nodes, excluding youtube/google domains, unwrapped through the redirect `q=` param, deduped, capped at 5.
**Invariant:** the retry is deliberately NOT a loop — YouTube intermittently serves bot-wall variants where extraction fails but HTTP was 200; one identity swap covers that while a longer loop would hammer. The consent cookie must be sent on EVERY request (not session-set) because requests sessions aren't used here. `links[0]` becomes `website`, feeding enrichment's deep-scrape — so redirect-unwrapping isn't cosmetic: an unwrapped link is the difference between scraping a real site and scraping google.com.
**Probe:** no direct test (zero-test repo). Commit `171503bf` ("fix: youtube scraper intermittent not found failures") is the live evidence this exact path needed hardening — deterministic probe pins: `grep -n "CONSENT\|_clean_redirect_url\|random_user_agent()" app/scrapers/youtube.py`.
**Coverage caveat:** pinned by source + git history only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "youtube channel consent subscriberCountText", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt identifier-routing + consent-cookie + bounded identity-swap retry for any Google-family property; adapt anchors when YT renames render keys; keep the redirect-unwrapping rule verbatim wherever outbound links feed downstream fetches.
