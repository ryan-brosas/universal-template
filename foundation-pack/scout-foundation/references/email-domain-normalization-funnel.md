<!-- capsule-v2 -->
# Website→domain normalization funnel — what happens to a raw 'website' string before any email is built from it?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How is a raw profile `website` value normalized into a mail domain, and where does normalization silently produce garbage instead of failing?

## LeadEnricher._extract_domain — one shared pre-domain step under both email generators AND the orchestrator
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._extract_domain` (:378–385).
**Signature:** `_extract_domain(self, website: str) -> Optional[str]`.
**Data Shape:** in: raw website value (bare host, with path, `www.`-prefixed, empty string, `None`); out: host-ish string or `None`; exactly **4 call sites** feed it — `enrich_lead`:71 (orchestrator's `work_domain`), `_predict_email_from_pattern`:251 (observe twin), `_generate_email_candidates`:454 (blind generator), `_find_company_domain`:512 (headline→domain path).

### Decisive source
```python
def _extract_domain(self, website: str) -> Optional[str]:
    try:
        if not website.startswith('http'):        # case-sensitive lowercase check
            website = 'https://' + website
        domain = urlparse(website).netloc or website   # fallback returns PREFIXED junk
        return domain.replace('www.', '')          # strips EVERY 'www.' occurrence
    except Exception:
        return None
```

**Flow:** prepend `https://` unless the string starts with lowercase `http` → take `urlparse(...).netloc`, falling back to the whole (already-prefixed) string when netloc parses empty → substring-strip every `www.` → return.
**Invariant:** only NON-STRING input yields `None` (`None.startswith` → AttributeError → except). Every *string* — including `''`, `'https://'`, `'//host'`, `'HTTP://HOST'` — returns some string: `''` → `'https://'` (netloc-empty fallback), uppercase scheme → `'HTTP:'` (double-prefix corruption), protocol-relative `'//acme.com'` → `'https:////acme.com'`. All four edge cases EXECUTED against real `urllib.parse` at pin. Consumers then build `{first}.{last}@{domain}` candidates and run them through the DNS-MX oracle, so malformed-but-string inputs become silently-wrong email domains (wasted SMTP probes at best, wrong-contact sends at worst) instead of skips. The case sensitivity of `startswith('http')` is load-bearing: `HTTPS://…` still gets prefixed.
**Probe:** zero-test repo; deterministic greps EXECUTED byte-exact at pin: `grep -n "def _extract_domain" app/scrapers/enrichment.py` → exactly 1 site `:378`; `grep -c "_extract_domain(" app/scrapers/enrichment.py` → **5** (= def line + 4 call sites :71/:251/:454/:512 — a count of 3 means a sibling call site appeared, re-census); `grep -n "replace('www.'" app/scrapers/enrichment.py` → exactly 1 site `:383`; `grep -c "startswith('http')" app/scrapers/enrichment.py` → **4**: this helper :380 plus the sibling scheme-prepend trio `_fetch_page`:197, `_deep_scrape_website`:211, `_extract_bio_links`:482 (those three are fetch-layer normalization owned by `bio-link-scavenging`/`contact-page-crawl`; only :380 feeds the mail-domain plane).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_extract_domain urlparse netloc website domain", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the normalize-then-fallback shape (scheme-prepend → netloc-or-whole → www-strip) as the single choke point EVERY mail-domain consumer funnels through before pattern inference or generation; adapt it to REJECT (return `None`) on empty-after-parse, uppercase-scheme, and protocol-relative outcomes if your downstream pays per candidate — Scout tolerates garbage because SMTP verify prices each probe; omit nothing, but record the three garbage-out classes as the reason this helper must stay upstream of both the observe-before-predict twin (`company-pattern-emails`) and the blind generator (`candidate-funnel`). Coverage caveat: pinned by executed greps + direct urllib execution; zero-test repo.
