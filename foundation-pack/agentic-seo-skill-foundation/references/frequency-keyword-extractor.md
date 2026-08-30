<!-- capsule-v2 -->
# frequency keyword extractor — how are keyword candidates ranked without a reference corpus?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** Why 3.0×/5.0× n-gram weights, and how does substring dedupe pick the final list?

## Weighted n-gram counter
**Path/Symbol:** `scripts/article_seo.py:extract_keywords_frequency` (:364-405), `STOP_WORDS` (:46-57), `get_google_autocomplete` (:412-424).
**Signature:** `extract_keywords_frequency(text: str, top_n: int = 12) -> list[str]`.
**Data Shape:** tokens = lowercase `\b[a-z]{3,}\b` minus ~90-stop-word set; returns up to 12 phrases ordered by weighted score.

### Decisive source
```python
for term, cnt in unigrams.items():
    if cnt > 3:
        scored.append((term, float(cnt)))
for term, cnt in bigrams.items():
    if cnt > 1:
        scored.append((term, cnt * 3.0))
for term, cnt in trigrams.items():
    if cnt > 1:
        scored.append((term, cnt * 5.0))
...
if not any(term in other and term != other for other in all_terms[:top_n * 3]):
```

**Flow:** tokenize (3+ letters only — digits excluded) → stop-word filter BEFORE n-gram construction (so bigrams never contain stop words) → unigrams need >3 occurrences scoring count×1; bigrams/trigrams need >1 scoring ×3.0/×5.0 → sort desc → substring dedupe: a candidate contained in ANY of the top-36 scored terms is dropped in favor of the longer phrase → truncate at top_n.
**Invariant:** The docstring's honesty is part of the contract — "frequency counting (not TF-IDF — no corpus reference available)". The ×3/×5 multipliers encode "phrases beat single terms" as an opinion, not math. Autocomplete (`suggestqueries.google.com/complete/search?client=chrome`) pads related-keywords to ≥5 from extracted list when the network yields little; failures return [] silently.
**Probe:** `grep -cF 'cnt * 3.0' scripts/article_seo.py` (= 1); `grep -cF 'cnt * 5.0' scripts/article_seo.py` (= 1); `grep -cF 'if cnt > 3:' scripts/article_seo.py` (= 1); direct test exercises `article_seo` via `tests/test_reporting.py` fixture pipeline.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"keywords frequency bigrams trigrams","limit":5}'`.

## Verdict
Adopt thresholded-weighted-n-grams + longer-phrase-wins dedupe for corpus-free keyword mining; adapt thresholds to language/corpus size; omit autocomplete padding for offline builds. Probes executed green @69199160.
