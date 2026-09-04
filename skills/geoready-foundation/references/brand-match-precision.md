<!-- capsule-v2 -->
# Brand-match precision — how do you count brand mentions without counting lookalike domains?

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** What regex shape distinguishes a real brand mention from substring noise and same-named domains?

## Conditional word boundaries + domain-root negative lookahead
**Path/Symbol:** `src/geo_optimizer/utils/brand_match.py:brand_pattern` (19–36).
**Signature:** `brand_pattern(brand) -> re.Pattern` (lru_cached, maxsize 256); `brand_matches(text, brand) -> bool`; `count_brand_mentions(text, brand) -> int`.
**Data Shape:** pattern = `LEFT \b? escaped-brand RIGHT \b? (?!\.\w)` case-insensitive.

### Decisive source
```python
escaped = re.escape(brand)
left = r"\b" if brand[:1].isalnum() or brand[:1] == "_" else ""
right = r"\b" if brand[-1:].isalnum() or brand[-1:] == "_" else ""
return re.compile(left + escaped + right + r"(?!\.\w)", re.IGNORECASE)
# Docstring: "Acme" must NOT match inside "Acmecorp"; "GeoReady" must not match
# "geoready.app" when the audited site is geoready.dev — but an inline mention,
# sentence-final mention, or C++/Yahoo!-style edge-punctuation brand MUST match.
```

**Flow:** compile once per brand (cached because one audit matches the same brand against many responses) → `search` for presence / `findall`+len for counts → used by citations verdicts, sentiment prompts, perception extraction.
**Invariant:** `\b` is only valid adjacent to a word char — forcing it on both sides of `C++` or `.NET` makes the brand UNMATCHABLE; the conditional-boundary rule is the fix. The `(?!\\.\w)` lookahead kills exactly the `brand.tld` host form while still matching `brand.` at sentence end (lookahead requires a following word char). A porter who substitutes naive `re.search(brand, text, re.I)` inflates mention metrics on every audit of a competitor-hosted domain.
**Probe:** `tests/test_brand_match.py` (dedicated 12-test module incl Acme/Acmecorp and geoready.app cases; `PYTHONPATH=src pytest tests/test_brand_match.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "brand_pattern boundary lookahead", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt verbatim for any entity-mention counting (brands, product names, competitor terms); adapt cache size; omit nothing else.
