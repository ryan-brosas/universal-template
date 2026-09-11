<!-- capsule-v2 -->
# Brand entity signals — KG pillars, about/contact discovery, name consistency across surfaces

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you score entity disambiguation readiness from soup + schema + meta without any network call?

## Consistency checks + pillar-domain sameAs counting
**Path/Symbol:** `src/geo_optimizer/core/audit_brand.py:audit_brand_entity` (244L whole module); constants `KG_PILLAR_DOMAINS` / `SAMEAS_AUTHORITATIVE_DOMAINS` / `BRAND_LEGAL_SUFFIXES` / `ABOUT_LINK_PATTERNS` in `models/config.py`.
**Signature:** `audit_brand_entity(soup, schema, meta, content) -> BrandEntityResult`.
**Data Shape:** outputs consumed by scoring (`brand_entity_coherence` 3pt = 2 name + 1 desc-match; `brand_kg_readiness` 3pt at ≥3 of 4 pillars; about/contact 2×1pt; geo identity 1pt via hreflang-or-geo-schema; topic authority 1pt at faq_depth≥3 or recent articles), trust identity/social layers, monitor entity signal, perception extractor.

### Decisive source
```python
# config: legal suffixes stripped from the END before comparison (#397)
BRAND_LEGAL_SUFFIXES: frozenset = frozenset({"inc","ltd","limited","llc","corp",
    "gmbh","s.r.l.","srl","s.p.a.","ag","co","plc","pty","bv","nv", ...})
# pillar domains — "the 4 most relevant" for Knowledge Graph disambiguation
KG_PILLAR_DOMAINS = {"wikipedia.org", "wikidata.org", "linkedin.com", "crunchbase.com"}
```

**Flow:** candidate names harvested from title, og:title, H1, Organization schema → normalized (casefold, punctuation strip, legal-suffix removal) → consistency = ≥2 sources agree on one canonical form (`names_found`, `primary_name`) → description match compares schema description to meta description (token overlap) → sameAs URLs scanned for pillar domains → about-link detected against a pattern list that includes non-English forms (/chi-siamo, /azienda); contact info from Organization address/telephone/contactPoint.
**Invariant:** Zero HTTP fetches — everything derives from data already on the page or in prior sub-audits; legal-suffix stripping happens only at NAME END after punctuation cleanup, so "Infinity Co" doesn't collapse into "Infinity"; the 3-pillar threshold (not 4) rewards near-complete KG wiring. This module is the single source feeding FOUR consumers — changing its field names breaks scorer/trust/monitor/perception simultaneously.
**Probe:** `tests/test_brand_entity_signals.py::test_name_consistency_across_surfaces` (+ pillar suites; `PYTHONPATH=src pytest tests/test_brand_entity_signals.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "brand entity kg_pillar_count", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt multi-surface name voting + suffix-aware normalization + pillar-count grading for entity scoring; adapt domain lists/patterns; omit hreflang logic if single-market.
