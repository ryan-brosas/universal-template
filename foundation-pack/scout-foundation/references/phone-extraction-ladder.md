<!-- capsule-v2 -->
# Phone extraction ladder — why do tel: links outrank visible-text regexes?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** In HTML full of digits, what ordering extracts the owner's real phone without false positives?

## Structured links first → WhatsApp deep-links → stripped-text NA patterns
**Path/Symbol:** `app/scrapers/enrichment.py:LeadEnricher._extract_phone_from_text` (:163-193).
**Signature:** `_extract_phone_from_text(text) -> Optional[str]`.
**Data Shape:** input may be raw HTML or plain text; digit-count validity window 10–15 (cleaned of non-`[\d+]`) gates EVERY tier; tier 1 `tel:` hrefs return the RAW attribute text; tier 2 wa.me / api.whatsapp.com/send?phone= returns '+' + digits; tier 3 operates on script/style-stripped, tag-stripped, whitespace-collapsed text against three NA-shaped patterns.

### Decisive source
```python
tel_links = re.findall(r'href=["\']tel:([+\d\s\-().]+)', text)
for tel in tel_links:
    clean = re.sub(r'[^\d+]', '', tel)
    if 10 <= len(clean) <= 15:        # same window as every other tier
        return tel.strip()            # RAW string kept — formatting is signal

wa_links = re.findall(r'(?:wa\.me|api\.whatsapp\.com/send\?phone=)(\d+)', text)
...
visible = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)
visible = re.sub(r'<style[^>]*>.*?</style>', '', visible, flags=re.DOTALL)
visible = re.sub(r'<[^>]+>', ' ', visible)
visible = re.sub(r'\s+', ' ', visible)

phone_patterns = [
    r'\+1[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',   # +1 country code
    r'\+?\d{1,3}[-.\s]\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', # intl with space/dash
    r'\(\d{3}\)[-. \s]?\d{3}[-.\s]?\d{4}',               # bare (XXX) XXX-XXXX
]
```

**Flow:** try tel: hrefs → WhatsApp link forms → only then scan visible text; first valid hit wins.
**Invariant:** structured signals (a page deliberately linking its number) always beat content scans — a porter who reorders these gets fax numbers and IDs from page copy. The 10–15 cleaned-digit window runs in EVERY tier because formatting varies but real numbers don't. Tier 1 preserves the original string (`tel.strip()`), tiers 2–3 normalize — callers must not assume a canonical format. The three patterns are North-America-shaped; international pages fall through to None by design (precision over recall).
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -n 'wa_links\|tel:' app/scrapers/enrichment.py` pins both structured tiers (:164 tel hrefs, :170 WhatsApp forms — anchor on the variable names; grepping `wa\.me` directly needs the source's backslash preserved through your shell quoting); `grep -c "10 <= len(clean)" app/scrapers/enrichment.py` = 2 (tel + visible tiers), plus the wa tier's own `10 <= len(num)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "_extract_phone_from_text phone patterns tel", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the structured-first ladder and the universal 10–15 digit window; adapt pattern set per market (add E.164/EU shapes if your targets are international — accept the recall hit); omit nothing. Note this helper is shared by bio text, deep-scraped pages, AND bio-link pages, so one fix upgrades all acquisition paths. Coverage caveat: pinned by source lines only.
