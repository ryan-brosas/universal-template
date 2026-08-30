<!-- capsule-v2 -->
# Candidate funnel + lead score — why does the best email win, and what makes a lead worth 100?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How do six independent discovery sources compete into one email field, and how is the final lead ranked?

## Source-tier base scores → SMTP adjust → argmax; additive 100-cap lead score
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher.enrich_lead` (funnel :31-137), `_score_and_verify_email` (:340-376), dedup block (:104-110), `_calculate_lead_score` (:535-564).
**Signature:** `_score_and_verify_email(email, source, pattern_match=False, site_emails_count=0) -> Dict{'email','score'≤100,'source','verified','accept_all'}`.
**Data Shape:** candidate tuples `(email, source)`; sources and base scores: bio=90, hunter.io=80, website=70, smtp_guess=70, bio_link=65, contact_page=60, pattern=40 (+15 if ≥3 site emails, +10 if ≥1); SMTP: exists +10, accept_all −20.

### Decisive source
```python
# dedupe case-insensitively, keep FIRST (highest-priority) source:
seen = set()
for email, source in email_candidates:
    if email.lower() not in seen:
        seen.add(email.lower()); unique.append((email, source))

best = None; best_score = -1
for email, source in unique:
    scored = self._score_and_verify_email(email, source, ...)
    if scored['score'] > best_score:      # strict > ⇒ first wins ties

# lead score — the "sweet spot" band is the interesting bit:
if 5000 <= followers <= 50000:   score += 15     # micro-influencer band
elif 1000 <= followers <= 100000: score += 10
elif followers > 0:               score += 5
bio_kw = ['coach','consultant','ceo','founder','entrepreneur','agency','business','owner','director','manager']
```

**Flow:** candidates accumulate from bio regex → useful-website deep scrape (`/contact`, `/contact-us`, `/about`, `/about-us` pages, early-break when both email+phone found) → company-domain scrape → pattern prediction → blind smtp_guess (only when zero candidates so far) → Hunter API (only when key+name+website present) → up to 3 bio links. Each is scored+SMTP-checked; argmax wins and writes `email/email_score/email_source/email_verified`. When nothing verified, `possible_emails` still lists 7 unverified guesses for human follow-up.
**Invariant:** insertion order IS priority — dedup keeps the earliest source's claim on an address, and strict `>` means earlier sources win score ties (bio email beats an equal-scoring website email). "Useful" website excludes the platform/link-in-bio domains list (`useless_domains`) so scraping youtube.com for contact info never happens. Lead score bands encode a sales thesis (5k–50k followers outscores celebrities) — port it as opinionated config, not truth. The `contact_page` score branch (:349) is DEAD at pin: `_deep_scrape_website` results always enter tagged `'website'`, so nothing ever emits `'contact_page'` — port the tag table minus that ghost row unless you wire a real contact-page emitter.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "email_candidates.append\|best_score" enrichment.py` pins all SEVEN append sites (:37 bio / :54 website-direct / :67 website-company-domain-fallback / :78 pattern / :85 smtp_guess / :93 hunter.io / :100 bio_link = six distinct tags, `website` twice) and the single argmax loop; graph retrieval resolves `Scout.app.scrapers.enrichment.LeadEnricher.enrich_lead`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "enrich_lead score best email candidates", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ordered-candidates + tiered-source-scores + argmax-with-first-wins-ties; adapt score weights and keyword lists per domain; omit the Hunter branch unless you hold a key (it appends AFTER cheaper sources deliberately — paid lookup is last resort). Note `enrich_bulk` (ThreadPoolExecutor(max_workers=3)) is dead upstream — the interactive path enriches serially to respect delays; record as omit-with-reason.
