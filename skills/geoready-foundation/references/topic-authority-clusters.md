<!-- capsule-v2 -->
# Topic authority clustering — DF-filtered term clusters, hub-and-spoke interlinking, pillar detection

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you score site-level topical authority from ≤20 crawled pages without an LLM?

## Term→pages inverted index minus boilerplate and brand terms
**Path/Symbol:** `src/geo_optimizer/core/topic_authority.py:_build_clusters` (73–128), `_score` (153–161), `run_topic_authority` (195+).
**Signature:** `run_topic_authority(sitemap_url, brand="", max_pages=20) -> TopicAuthorityResult`.
**Data Shape:** weights sum 100 — coverage 40 (strongest cluster vs `_COVERAGE_TARGET=5` pages), interlink 30 (mean ratio of cluster members linking to a sibling), pillars 20 (share of clusters whose pillar page has the term in title/H1), breadth 10 (distinct clusters vs `_BREADTH_TARGET=3`); `_MIN_CLUSTER_PAGES=2`, boilerplate DF >0.8 when ≥5 pages analyzed.

### Decisive source
```python
for extract in extracts:
    for term in extract.key_terms:
        key = term.lower()
        # The brand name appears everywhere by definition — it is identity,
        # not a topic, and would form one giant meaningless cluster.
        if brand_norm and brand_norm in re.sub(r"\W+", "", key):
            continue
        ...
apply_df_filter = len(extracts) >= _BOILERPLATE_MIN_PAGES   # menu labels live on every page
if apply_df_filter and len(pages) / len(extracts) > _BOILERPLATE_DF:
    continue

pillar_url = next((url for url in pages if key in titles.get(url, "")), "")   # title/H1 mention = pillar
interlinked = sum(1 for url in pages
                  if page_links.get(url, set()) & (normalized_pages - {_normalize_page_url(url)}))
```

**Flow:** reuse the coherence pipeline (`fetch_sitemap` + `term_extractor.extract_page_terms` per page, capped 20) → build inverted index with per-page dedupe and punctuation-insensitive brand exclusion → cluster terms by shared page sets → per-cluster interlink count via normalized same-host link-set intersection → aggregate weighted score + recommendations.
**Invariant:** URL identity normalization (strip fragment/trailing slash, drop www) must match between the link graph and cluster membership or interlink counts collapse to zero; the DF filter activates only at ≥5 pages because a ratio over 2–4 pages is noise; brand exclusion happens on `\W`-stripped lowercase so "Geo Ready" catches "GeoReady".
**Probe:** `tests/test_topic_authority.py::test_brand_term_excluded_from_clusters` (+ scoring suites; `PYTHONPATH=src pytest tests/test_topic_authority.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "topic authority clusters interlink", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt inverted-index clustering + DF gating + normalized link-graph intersection for site-level content analysis; adapt weights; omit the fixed weight table if you re-tune.
