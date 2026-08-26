<!-- capsule-v2 -->
# Contact-page crawl — how does the enricher mine a website for contacts, and what exactly ends the crawl?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** Which pages does `_deep_scrape_website` visit, when does it stop early, and what guarantees does its returned dict carry?

## Fixed five-path crawl with two-signal early exit
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._deep_scrape_website` (:208-247), shared primitives `_fetch_page` (:195-206), `_is_valid_email` (:155-161), `_extract_phone_from_text` (:163-193); text-tier twin `_extract_from_text` (:139-153); single-link sibling `_scrape_link_page` (:489-505).
**Signature:** `_deep_scrape_website(website: str) -> Dict{'email': Optional[str], 'phone': Optional[str], 'all_emails': List[str]}`.
**Data Shape:** input host or URL (scheme repaired to `https://` if missing — never validated further); output starts `{'email': None, 'phone': None, 'all_emails': []}` and mutates toward filled.

### Decisive source
```python
pages_to_check = [
    website,
    website.rstrip('/') + '/contact',
    website.rstrip('/') + '/contact-us',
    website.rstrip('/') + '/about',
    website.rstrip('/') + '/about-us',
]
for url in pages_to_check:
    html = self._fetch_page(url)          # fail-open: None on any error/non-200
    if not html:
        continue
    ...
    if result['email'] and result['phone']:
        break                              # BOTH required — one alone keeps crawling
    random_delay(0.3, 0.8)                 # fires on EVERY non-terminal page,
                                           # incl. pages that just yielded an email
result['all_emails'] = list(set(all_emails))   # set() ⇒ arbitrary order
```

**Flow:** scheme-repair → fixed path list (root, `/contact`, `/contact-us`, `/about`, `/about-us`) → per page: fail-open fetch → `EMAIL_RE` findall → blacklist/file-ext validation (`_is_valid_email`) → first valid becomes `email` if still unset → structured-first phone ladder over the raw HTML → break only when **both** signals present → polite `random_delay(0.3, 0.8)` between remaining pages → `all_emails` set-deduped at return. `_extract_from_text` (:139-153) is the bio-only twin: same regex+validation email tier plus delegation to the phone ladder, called exactly once on `lead_data['bio']` at :35 to seed the `'bio'` candidate. `_scrape_link_page` reuses the same fetch/validate/phone trio for one bio-link URL.
**Invariant:** the early exit needs email **and** phone — a contact page yielding only an address never shortens the crawl, and the delay fires after every page that didn't terminate it (including one that just found the email). `result['email']` is *first-valid-on-first-yielding-page*, not best; `all_emails` loses insertion order via `set()` — downstream code must not treat it ranked (only `len(site_emails)` feeds pattern-confidence). No page limit beyond the fixed five; no robots/sitemap awareness; every failure mode degrades to skip-and-continue.
**Probe:** no direct test (zero-test repo). Deterministic probes: `grep -cF "rstrip('/') +" app/scrapers/enrichment.py` → **4** (the four suffixed paths); `grep -nF "if result['email'] and result['phone']:" app/scrapers/enrichment.py` → exactly **:241**; `grep -cF "_extract_from_text(lead_data.get('bio', ''))" app/scrapers/enrichment.py` → **1**.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "deep scrape website contact about pages", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fixed-path ladder + two-signal early exit + fail-open fetch as a portable polite-crawl primitive (it's why Scout never hammers a site for one address); adapt the path list and delays to your targets' conventions; omit the set()-dedup ordering assumption anywhere you need ranked evidence. Coverage caveat: `check_index_coverage` on `app/scrapers/enrichment.py` reports `no_recorded_issue / metadata_match` (best-effort signal only).
