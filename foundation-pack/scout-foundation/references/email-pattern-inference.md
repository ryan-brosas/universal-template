<!-- capsule-v2 -->
# Observe-before-predict email pattern inference — how do you learn a company's address convention from one real sample?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** How does the code infer `first.last@` vs `flast@` style from scraped addresses instead of guessing blind?

## Sample-local-part → 3-pattern detector → template apply → echo-if-already-known
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._predict_email_from_pattern` (:249-276), `_detect_pattern` (:278-289), `_apply_pattern` (:291-299).
**Signature:** `_predict_email_from_pattern(full_name, website, site_emails: List[str]) -> Optional[str]`; `_detect_pattern(local_part) -> Optional['first.last'|'f.last'|'first']`.
**Data Shape:** requires ≥2 name parts (`parts[0]`, `parts[-1]`); needs ≥1 site email ending `@<domain>`; templates: first.last / first / f.last / flast / firstlast.

### Decisive source
```python
domain_emails = [e for e in site_emails if e.lower().endswith('@' + domain)]
if not domain_emails:
    return None                      # NO sample ⇒ NO prediction (contrast with _generate)
sample = domain_emails[0].lower()
local = sample.split('@')[0]
pattern = self._detect_pattern(local)
if not pattern:
    return None
predicted = self._apply_pattern(pattern, first, last, domain)
if predicted and predicted.lower() not in [e.lower() for e in domain_emails]:
    return predicted

return predicted                     # ← dead-looking line IS the contract:
                                     #   predicted already on site ⇒ return it unchanged,
                                     #   so the funnel scores 'pattern' for a VERIFIED address
```

**Flow:** filter site emails to the target domain → take FIRST as the convention sample → classify its local part (`.`-split with single-char head = f.last; plain letters = first; `x.rrrr` = f.last; else None) → render the person's name through that template.
**Invariant:** prediction only happens AFTER observation — with zero domain samples this returns None and the funnel falls through to blind smtp_guess; a porter "simplifying" to always-generate destroys the observe-first guarantee (the two generators are NOT interchangeable). The final unconditional return means an address matching an existing scrape is still emitted as source='pattern' — deliberate: it re-verifies and re-scores a known-good contact rather than dropping it.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n "_generate_email_candidates\|_predict_email_from_pattern" app/scrapers/enrichment.py` — predict called ONLY at :74 inside the site-emails guard; generate at :81 (empty-funnel branch) and :132 (possible_emails fallback); `grep -n "return predicted" app/scrapers/enrichment.py` shows both exits (:274 guarded, :276 unconditional).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_predict_email_from_pattern _detect_pattern local part", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt observe-before-predict (one real sample pins the convention) and the twin-generator split (sampled prediction vs blind enumeration); adapt `_detect_pattern`'s regex set to conventions your locale actually uses (initial+dot is regional); omit nothing — but note only 3 of 5 templates are reachable from detection (flast/firstlast exist for future detectors), and the unconditional-return tail looks like a bug but is the re-scoring contract. Coverage caveat: pinned by source lines only.
