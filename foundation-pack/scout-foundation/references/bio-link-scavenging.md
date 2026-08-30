<!-- capsule-v2 -->
# Bio-link scavenging + shared fetch primitive — how does a bio string become extra contact sources?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How are bare `linktr.ee/x` mentions turned into fetchable URLs, and what contract does the shared `_fetch_page` impose?

## URL-or-bare-host regex → 3-link budget → permissive fetch with scheme repair
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._extract_bio_links` (:473-487), `_scrape_link_page` (:489-505), `_fetch_page` (:195-206).
**Signature:** `_extract_bio_links(bio) -> List[str]`; `_scrape_link_page(url) -> Dict{'email','phone'}`; `_fetch_page(url) -> Optional[str html>`.
**Data Shape:** bio-link regex matches full URLs OR bare `linktr.ee|stan.store|beacons.ai/<path>`; cleaned with scheme prepend + trailing-punct rstrip `'.,;:!?)'`; link budget = first **3** (`bio_links[:3]`); fetch: 10s timeout, `follow_redirects=True`, fresh `random_user_agent()` per call, non-200/exception → None.

### Decisive source
```python
url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+|(?:linktr\.ee|stan\.store|beacons\.ai)/[^\s<>"{}|\\^`\[\]]+'
links = re.findall(url_pattern, bio)

cleaned = []
for link in links:
    if not link.startswith('http'):
        link = 'https://' + link      # scheme repair for bare hosts
    link = link.rstrip('.,;:!?)')     # sentence punctuation is NOT part of the URL
    cleaned.append(link)
```

**Flow:** regex the bio → repair schemes/punctuation → for up to 3 links, fetch and run the same email/phone extractors used on main sites.
**Invariant:** the char-class exclusion set `` [^\s<>"{}|\\^`[] `` mirrors RFC-safe URL characters — it stops at HTML delimiters AND markdown parens, which is why the rstrip ladder only needs trailing punctuation (leading/side punctuation can't be captured). `_fetch_page` is deliberately PERMISSIVE: any exception → None, no retries — enrichment must never crash a scrape batch, it degrades to "fewer candidates." Fresh UA per call (vs tiktok's frozen client) because these are third-party pages with independent bot defenses. The 3-link cap bounds total runtime: each link costs a live HTTP round-trip.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "linktr\\.ee|stan\\.store\|beacons" app/scrapers/enrichment.py` pins the bare-host alternation (:477); `grep -n "bio_links\[:3\]" app/scrapers/enrichment.py` pins the budget (:97); `grep -c "except Exception" app/scrapers/enrichment.py` ≥ 4 (fetch/hunter/domain paths all degrade).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_extract_bio_links _scrape_link_page _fetch_page", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bare-host alternation trick (bio text often names link-in-bio hosts without scheme) and the bounded-scavenge pattern; adapt the host list to your market's link-in-bio services; omit nothing. Note `_scrape_link_page` reuses `_is_valid_email` blacklists, so junk domains like `wordpress.com` in scraped mailtos never leak into candidates. Coverage caveat: pinned by source lines only.
