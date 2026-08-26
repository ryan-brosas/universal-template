<!-- capsule-v2 -->
# citation-readiness scoring — how do you score a page's capacity to back AI-answer citations?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What counts as a "factual claim", how is claim coverage computed, and what is the additive score ceiling?

## Claim/citation ratio scorer
**Path/Symbol:** `scripts/citation_readiness.py:check_citation_readiness` (:66-131), `CLAIM_RE` (:14-17), `HIGH_TRUST_HOST_RE` (:18-20), `_schema_entity_signals` (:47-60).
**Signature:** `check_citation_readiness(source: str, timeout: int = 15) -> dict` (score ≤ 100).
**Data Shape:** Returns `{url, score, factual_claims, claim_samples(≤10), citation_signals{external,trusted,cite_tags,footnotes}, entity_signals{types,names,sameAs}, issues, fetch_error}`.

### Decisive source
```python
citation_capacity = len(external_links) + len(cite_tags) + len(footnote_links)
claim_coverage = min(1.0, citation_capacity / max(1, len(factual_claims)))
score += int(claim_coverage * 35)
score += min(20, len(trusted_links) * 5)
score += 15 if author_signals else 0
score += min(20, len(entity_signals["sameAs"]) * 5)
score += 10 if parsed.get("canonical") else 0
```

**Flow:** split body into sentences → `CLAIM_RE` flags percentages, dollar amounts, years 19xx/20xx, and evidence verbs ("study", "according to", "found that", "shows that") plus superlatives ("largest/first/only/most") as factual claims → citation capacity = external links + `<cite>/<blockquote>` + footnote-ish links → coverage ratio capped at 1.0 with `max(1,…)` zero-guard → additive ladder: 35 coverage + trusted-domain links ×5 capped 20 (gov/edu/who.int/nih/cdc/worldbank/oecd/wikipedia regex) + author-or-entity-name signal 15 + JSON-LD sameAs ×5 capped 20 + canonical 10 → floor-capped at 100.
**Invariant:** The three caps (35/20/20) mean a link farm cannot buy a perfect score — saturation forces diversity across signal CLASSES. Zero claims ⇒ coverage 1.0 ⇒ free 35 points by design (nothing to cite).
**Probe:** `grep -cF 'int(claim_coverage * 35)' scripts/citation_readiness.py` (= 1); `grep -cF 'min(20, len(trusted_links) * 5)' scripts/citation_readiness.py` (= 1); direct test `tests/test_content_ai_scripts.py::test_content_eeat_freshness_answer_and_citation_scripts` asserts `trusted_external_links == 1` on the fixture.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"citation readiness factual claims trusted","limit":5}'`.

## Verdict
Adopt the class-diversified additive scoring shape for any citability metric; adapt the trust-host roster and claim vocabulary to locale/domain; omit the year-regex claim trigger if your corpus is time-insensitive. Probe executed green @69199160; fixture test green in the 34/34 run.
