<!-- capsule-v2 -->
# answer-block snippet grammar — what page formatting earns featured-snippet / AI-answer eligibility?

**Source:** Agentic-SEO-Skill MIT `main@69199160`; Codebase Memory `ext-aeo-agentic-seo-skill`. **Question:** What exact structural patterns does the scanner score, and why are the word windows load-bearing?

## Snippet-format scanner
**Path/Symbol:** `scripts/answer_block_scanner.py:scan_answer_blocks` (:29-101), `QUESTION_RE` (:11), `DEFINITION_RE` (:12).
**Signature:** `scan_answer_blocks(source: str, timeout: int = 15) -> dict` (score ≤ 100).
**Data Shape:** `{url, score, questions(≤50), direct_answers(≤50), definitions(≤50), lists(≤50), tables(≤50), issues, fetch_error}`; each direct answer = `{question, answer[:320], word_count}`.

### Decisive source
```python
if sibling.name in {"p", "div"} and 20 <= words <= 70:
    direct_answers.append(...)
...
score = min(100, len(direct_answers) * 20 + len(definitions) * 12
            + len(lists) * 10 + len(tables) * 12)
```

**Flow:** headings h1-h6 matching question grammar (interrogative stem OR trailing `?`) → walk to the next non-script/style SIBLING → count its words: a `p`/`div` of 20-70 words is a "direct answer" → paragraphs of 20-80 words matching `X is/are/refers to/means …` (20-220 continuation chars) are definitions → lists need ≥3 items (top-level `li` only), tables ≥2 rows with headers sampled → weighted sum 20/12/10/12 capped at 100.
**Invariant:** The windows ARE the featured-snippet thesis — Google extracts ~40-60-word answers, so sub-20 and over-70 siblings deliberately earn nothing. Lists require ≥3 items because a 2-item list isn't a listicle. Score saturates at 5 direct answers.
**Probe:** `grep -cF '20 <= words <= 70' scripts/answer_block_scanner.py` (= 1); `grep -cF '20 <= _word_count(text) <= 80' scripts/answer_block_scanner.py` (= 1); `grep -cF 'if len(items) >= 3:' scripts/answer_block_scanner.py` (= 1); fixture test asserts `direct_answers` + `lists` + `tables` all non-empty on the crafted HTML.
**Retrieve:** `codebase-memory-mcp cli search_graph '{"project":"ext-aeo-agentic-seo-skill","query":"answer block direct answers definition","limit":5}'`.

## Verdict
Adopt the four-pattern grammar (Q-heading→sibling-answer, definition paragraph, 3+ list, 2+ table) as the snippet-readiness contract; adapt word windows only with evidence; omit the `<div>` sibling acceptance if you want strict paragraph answers. Probes executed green @69199160; fixture test green in 34/34 run.
