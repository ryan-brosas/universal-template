<!-- capsule-v2 -->
# Contact extraction — why do utils.py and enrichment.py each own a phone extractor, and which regexes run where?

**Source:** Scout MIT `main@171503bf`; Codebase Memory `Scout`. **Question:** Where does email/phone parsing happen for a scraped profile, and what does the cheap tier guarantee?

## Two-tier split: shared regex utils vs HTML-aware enricher
**Path/Symbol:** `app/scrapers/utils.py:extract_email` (:16-22), `extract_phone` (:25-40), `parse_abbreviated_number` (:43-58); `enrichment.py:_extract_phone_from_text` (:163-193), `_is_valid_email` (:155-161).
**Signature:** `extract_email(text: str) -> str` (first match, `''` if none); `extract_phone(text) -> str` (digits+leading `+`, len ≥ 10); `parse_abbreviated_number(s) -> int` (`11.5K`→11500; unparsable → `0`, never raises).
**Data Shape:** scrapers call the cheap pair on bio text only at profile-build time; the enricher's version runs later over full HTML.

### Decisive source
```python
# utils.extract_phone — plain-text ladder
for pattern in patterns:
    matches = re.findall(pattern, text)
    if matches:
        phone = re.sub(r'[^\d+]', '', matches[0])
        if len(phone) >= 10:
            return phone

# enrichment._extract_phone_from_text — structured sources FIRST:
tel_links = re.findall(r'href=["\']tel:([+\d\s\-().]+)', text)     # tel: links beat prose
...
wa_links = re.findall(r'(?:wa\.me|api\.whatsapp\.com/send\?phone=)(\d+)', text)
...
visible = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)   # THEN strip
visible = re.sub(r'<[^>]+>', ' ', visible)                                  # tags → spaces
```

**Flow:** every scraper embeds `'email': extract_email(bio), 'phone': _extract_phone(bio)` in its returned dict (instagram additionally re-parses bio via the module-level aliases `_extract_email = extract_email`); enrichment later upgrades phones from website HTML using tel:/WhatsApp links before falling back to visible-text regexes.
**Invariant:** the tiers are not duplicates — utils has no HTML awareness and no blacklist; the enricher strips script/style blocks BEFORE matching (otherwise inline JS digits create phantom numbers) and validates emails against `EMAIL_BLACKLIST` (docs/vendor domains like wixpress.com, schema.org) + file-extension endings. The upper-bound check differs too: utils accepts ≥10 cleaned digits, the enricher bounds 10–15. `parse_abbreviated_number` returns 0 on garbage because follower counts feed arithmetic (`sum(scores)//len`) downstream — an exception there would crash whole batches.
**Probe:** no direct test (zero-test repo). Deterministic probe: `grep -rn "extract_email(bio)\|_extract_phone(bio)" app/scrapers/` pins per-platform embedding; graph retrieval resolves `Scout.app.scrapers.utils.extract_email`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Scout", query: "parse_abbreviated_number extract_phone", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt both tiers as-is — they answer different porting questions (bio-sniffing vs page-scraping); adapt the regex sets to your locales; omit nothing here except note utils' email regex is case-insensitive-TLD only and rejects no domains (that's the enricher's job).
