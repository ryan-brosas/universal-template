<!-- capsule-v2 -->
# DNS-oracle company-domain guessing — how do you find a company's domain from a headline with no API?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How is a company name extracted from free-text and converted into a live domain without any lookup service?

## Headline-marker extraction → TLD ladder → MX-resolution as existence oracle
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._find_company_domain` (:387-426), `_guess_domain` (:428-451).
**Signature:** `_find_company_domain(lead_data: Dict) -> Optional[str]`; `_guess_domain(company_name) -> Optional[str]`.
**Data Shape:** inputs read only `company`, `headline`, `bio`; candidate names deduped case-insensitively, length>2, first **3** tried (`unique_companies[:3]`); guess order: `{slug}.com → {slug}.io → {slug}.co → {w1}{w2}.com` (two-word names only); slug = lowercase minus non-`[a-z0-9]` with corporate suffixes `(inc|llc|ltd|co|corp|group|holdings)\.?$` stripped.

### Decisive source
```python
for marker in [' at ', ' @ ', ' - ']:        # "Jane Doe at Acme" style headlines
    if marker in headline:
        parts = headline.split(marker)
        if len(parts) >= 2:
            company_names.append(parts[-1].strip().rstrip('.'))

patterns = [
    r'(?:CEO|CTO|COO|CFO|Founder|Owner|Director|President|Partner)\s+(?:of|at|@|-)\s+(.+?)(?:\s*[|,.]|$)',
    r'(?:at|@)\s+(.+?)(?:\s*[|,.]|$)',
]
...
for domain in guesses:
    try:
        dns.resolver.resolve(domain, 'MX')   # the oracle: DNS answers, domain exists
        return domain
    except Exception:
        continue
```

**Flow:** collect candidates (explicit company field, marker split, two title regexes) → clean/dedupe → for up to 3 names, slugify, strip suffixes, try the 3–4 TLD guesses in order, return the FIRST whose DNS has MX records.
**Invariant:** an MX record is treated as PROOF of a real mail-capable domain — that's what makes a guessed domain safe to feed `_predict_email_from_pattern`/SMTP later. The ladder is ordered by likelihood (.com > .io > .co > concatenation), so porters adding TLDs must keep cheap/common-first ordering. Title regexes are deliberately narrow (`(.+?)(?:\s*[|,.]|$)` stops at separators) to avoid swallowing taglines.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "dns.resolver.resolve" app/scrapers/enrichment.py` → exactly 2 sites (:309 SMTP MX-pick, :446 domain oracle); `grep -n "inc|llc|ltd|co|corp|group|holdings" app/scrapers/enrichment.py` pins the suffix strip; `grep -cn "' at '" app/scrapers/enrichment.py` = 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_guess_domain _find_company_domain dns resolve domain", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt DNS-as-oracle existence checking (works offline from any paid data source, no rate limits beyond resolver latency); adapt the TLD set, corporate-suffix list, and headline markers per locale; omit nothing — but record that this guesses WRONG silently whenever a company's real domain isn't slug-shaped (e.g. "Acme Corp" → acme.com may be a squatter with MX records), so downstream pattern emails inherit the error. Coverage caveat: pinned by source lines only.
