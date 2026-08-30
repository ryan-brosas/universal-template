<!-- capsule-v2 -->
# Rehydration JSON extraction — how do TikTok, Pinterest, and Linktree turn one script tag into structured profiles?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** What is the shared "find the hydration script, parse, walk to the payload" pattern and how does each platform differ?

## Three hydration idioms: fixed-scope walk, recursive find, NEXT_DATA fallback
**Path/Symbol:** `app/scrapers/tiktok.py:scrape_tiktok_profile` (:57-79); `app/scrapers/pinterest.py:_extract_profile_data/_find_user_in_pws` (:74-169); `app/scrapers/linktree.py:_parse_linktree/_parse_generic` (:116-155/:191-228).
**Signature:** tiktok: `<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__">` → `data['__DEFAULT_SCOPE__']['webapp.user-detail']['userInfo']`; pinterest: `<script id="__PWS_DATA__">` → recursive search; linktree: `<script id="__NEXT_DATA__">` → `props.pageProps.account`.
**Data Shape:** all three regex the script body with `(.*?)</script>` + `re.DOTALL`, then `json.loads`; failure falls through to a degraded path rather than raising.

### Decisive source
```python
# pinterest — depth-capped recursive match on username+shape:
def _find_user_in_pws(data, username, depth=0):
    if depth > 15:
        return None
    if isinstance(data, dict):
        if data.get('username','').lower() == username.lower() and 'follower_count' in data:
            return {...}
        for value in data.values():
            result = _find_user_in_pws(value, username, depth + 1)
            if result: return result

# linktree — structured parse degrades to generic href scraping:
try:
    data = json.loads(data_match.group(1))
    account = data.get('props', {}).get('pageProps', {}).get('account', {})
    if not account:
        return None
except json.JSONDecodeError:
    return _parse_generic(html, username, 'linktree')   # NOT an error — a fallback
```

**Flow:** tiktok has the tightest contract (fixed key path; KeyError/TypeError → None) but NO not-found detection beyond HTTP 404/raise_for_status. Pinterest doesn't know where the user object lives, so it recursively hunts for "a dict whose username matches AND carries follower_count" (shape check disambiguates other users mentioned in data), capped at depth 15 against pathological nesting. Linktree treats NEXT_DATA as optional: absent or malformed JSON silently downgrades to `_parse_generic`, which scrapes raw hrefs and skips favicon/static/css/js URLs.
**Invariant:** the shape-check (`username matches` AND `follower_count present`) is what makes recursive search safe — matching username alone would hit unrelated nested user objects; depth-cap prevents stack exhaustion on adversarial markup. Degraded-mode parsing must produce the SAME profile dict shape as the structured path (linktree guarantees this) so downstream consumers can't tell which parser ran.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "__UNIVERSAL_DATA\|__PWS_DATA__\|__NEXT_DATA__" app/scrapers/*.py` pins all three anchors; graph retrieval resolves `Scout.app.scrapers.tiktok.scrape_tiktok_profile`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "__UNIVERSAL_DATA_FOR_REHYDRATION__ tiktok", limit: 5 });
```

## Verdict
Adopt the id-tagged-script→json.loads→walk pattern with shape-verified recursion and structured-to-generic degradation for ANY SPA-style target; adapt ids/key-paths per site; omit none of the three idioms — they cover the known variation space (fixed scope / unknown location / optional).
