<!-- capsule-v2 -->
# Company-domain + pattern prediction — how do you invent someone's work email from a headline alone?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How is a company extracted from free-text headlines, converted to a plausible domain, and used to predict the local-part convention?

## Headline mining → suffix-strip → MX-guess → observe-and-apply
**Path/Symbol:** `app/scrapers/enrichment.py:_find_company_domain` (:387-426), `_guess_domain` (:428-451), `_predict_email_from_pattern` (:249-276), `_detect_pattern` (:278-289), `_apply_pattern` (:291-299).
**Signature:** `_guess_domain(company_name: str) -> Optional[str]`; `_detect_pattern(local_part: str) -> 'first.last'|'f.last'|'first'|None`.
**Data Shape:** headline markers: `' at '`, `' @ '`, `' - '` splits take the LAST segment; role regexes `(?:CEO|CTO|COO|CFO|Founder|Owner|Director|President|Partner)\s+(?:of|at|@|-)\s+(.+?)(?:\s*[|,.]|$)`.

### Decisive source
```python
def _detect_pattern(self, local_part):
    if '.' in local_part:
        parts = local_part.split('.')
        if len(parts) == 2:
            if len(parts[0]) == 1: return 'f.last'
            return 'first.last'
    if re.match(r'^[a-z][a-z]+$', local_part): return 'first'
    return None

domain_emails = [e for e in site_emails if e.lower().endswith('@' + domain)]
sample = domain_emails[0].lower()
predicted = self._apply_pattern(self._detect_pattern(sample.split('@')[0]), first, last, domain)

# _guess_domain: legal-suffix strip then TLD ladder, MX probe = existence oracle
clean = re.sub(r'\s+(inc|llc|ltd|co|corp|group|holdings)\.?$', '', clean, flags=re.IGNORECASE)
slug = re.sub(r'[^a-z0-9]', '', clean)
for domain in [f'{slug}.com', f'{slug}.io', f'{slug}.co']:
    try:
        dns.resolver.resolve(domain, 'MX'); return domain
    except Exception:
        continue
```

**Flow:** up to three unique cleaned company names get domain-guessed; the first with ANY MX record wins (MX presence = the company probably owns it). Pattern prediction requires ≥1 real same-domain email as a template: detect ITS local-part shape ('first.last'/'f.last'/'first') and reapply to the target's first/last name. Only when NO site emails exist does the code fall to blind `_generate_email_candidates` (7 templates incl. contact@/info@) with SMTP verification of the first 5.
**Invariant:** prediction is evidence-first — never guess a convention when the domain itself has shown you one; the single-letter guard (`len(parts[0]) == 1`) is what separates 'j.smith' from 'john.smith'. Slug building strips ALL non-alphanumerics (spaces vanish entirely: "Acme Corp"→"acmecorp.com"), and the two-word special-case guess joins parts WITHOUT separator.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "_detect_pattern\|_guess_domain\|_generate_email_candidates" enrichment.py` pins the chain (:268, :422, :81/:132); graph retrieval resolves `Scout.app.scrapers.enrichment.LeadEnricher._find_company_domain`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "company domain headline pattern predict email", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt observe-before-predict and the MX-as-existence-oracle trick; adapt the role regexes and TLD ladder per market; omit the `.co` guess if false positives annoy you (any short domain with MX matches). Coverage caveat: pinned by source only.
