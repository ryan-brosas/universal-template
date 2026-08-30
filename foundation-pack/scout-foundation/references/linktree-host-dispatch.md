<!-- capsule-v2 -->
# Link-in-bio host dispatch — how does one module serve four hosts with per-host parse strategies, and what must be true before a result may win?

**Source:** Scout MIT `main@171503bf8c56d61fd6462ff08c557ec0b7fafa34`; Codebase Memory `Scout`. **Question:** What does the shared fetch layer guarantee (normalization, status triage, timeouts) and why do per-host parsers carry content-presence gates?

## Template-URL registry → status triage → three-way parse dispatch with empty-shell rejection

**Path/Symbol:** `app/scrapers/linktree.py` — `PLATFORMS` (:29-34), thin wrappers `scrape_linktree/scrape_stan/scrape_linkr/scrape_biolink` (:37-54), `scrape_all` first-hit probe (:57-63), **`_scrape_profile` fetch+dispatch (:66-113)**, `_parse_stan` (:158-188), `_parse_generic` content gate (:211-212), `_parse_linktree` account gate (:127-128), alias `_extract_email = _shared_extract_email` (:285).

**Signature:** `_scrape_profile(username: str, platform: str) -> Optional[Dict]`; `PLATFORMS: dict[name → 'https://host/{username}']`.

**Data Shape:** username normalization `.lstrip('@').strip().lower()` applied INSIDE `_scrape_profile` (every entry point benefits); fetch `requests.get(url, timeout=20)`; success dict carries exactly 12 keys (`username, full_name, bio, email, follower_count, website, links, link_count, socials, platform, profile_url` — `follower_count` always literal 0 here).

### Decisive source

```python
def _scrape_profile(username, platform):
    username = username.lstrip('@').strip().lower()
    if platform not in PLATFORMS:
        logger.error(f"Unknown platform: {platform}")
        return None                                  # loud log, quiet None
    url = PLATFORMS[platform].format(username=username)
    ...
    r = requests.get(url, headers=headers, timeout=20)
    if r.status_code == 404:
        logger.debug(...)                            # EXPECTED case → debug
        return None
    if r.status_code != 200:
        logger.error(...)                            # surprise → error
        return None
    html = r.text
    if platform == 'linktree':
        return _parse_linktree(html, username)       # structured, degrades
    elif platform == 'stan':
        return _parse_stan(html, username)           # regex-only host
    else:
        return _parse_generic(html, username, platform)

# stan: no structured API — regex name/description OUT of raw HTML,
# hrefs harvested EXCLUDING the host's own domain:
link_matches = re.findall(r'href="(https?://[^"]+)"', html)
for url in link_matches:
    if 'stan.store' not in url and url.startswith('http'):
        links.append({'title': '', 'url': url})
...
if not full_name and not links:
    return None                                      # empty shell rejected

# generic: requires at least one link to answer
if not links:
    return None
```

**Flow:** template URL → GET (20 s) → status triage → per-platform parser. Three trust tiers coexist behind ONE dispatch: linktree trusts `__NEXT_DATA__` JSON but degrades to `_parse_generic` on missing script OR `JSONDecodeError` (degradation contract owned by `rehydration-extraction.md`); stan has NO structured fallback — it regexes `"name":"…"` / `"description":"…"` straight out of markup; generic parses `<title>` + meta-description + deduped hrefs minus favicon/static/assets/.css/.js noise. Every candidate dict passes a content-presence gate (stan: name OR links; generic: ≥1 link; linktree: non-empty `account`) before returning.

**Invariant:** (1) 404 and non-200 get DIFFERENT log levels because multi-host probing expects most users to be absent from most hosts — treating 404 as error floods logs during `scrape_all`; (2) the content gates are what make `scrape_all`'s first-hit-wins safe: without them a bare stan shell (200 OK, zero content) would claim the username and SHADOW a real bio.link page probed later — a porter who "simplifies" the gates breaks identity resolution, not just cosmetics; (3) all parsers return the same 12-key shape so downstream consumers cannot tell which ran; (4) the module tail aliases `_extract_email = _shared_extract_email` so every parser's `'email': _extract_email_from_links(links) or _extract_email(bio)` reads as one mailto-first ladder (mailto beats bio-regex; see `linkbio-resolution.md`). Self-host exclusion in stan's harvest (`'stan.store' not in url`) is the same self-reference block as `_extract_website`'s domain list — both must be extended when adding a host to `PLATFORMS`.

**Probe:** no upstream tests (zero-test repo). Deterministic pins: `grep -n "Unknown platform\|status_code == 404\|return _parse_" app/scrapers/linktree.py` → :77/:91/:102/:104/:106. Executable (no network): `python3 -c "import sys; sys.path.insert(0,'<repo>'); from app.scrapers.linktree import _scrape_profile; assert _scrape_profile('x','bogus') is None"` exercises the unknown-platform guard live.

**Retrieve:**

```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_scrape_profile platform dispatch linktree stan generic status", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the template-registry + status-triage + per-host-parser-dispatch skeleton and the content-presence gates as one portable unit (~120 lines); adapt the host table, per-host parse strategy, and exclusion lists to your targets; omit nothing — the gates ARE the correctness argument for first-hit multi-host probing.
