<!-- capsule-v2 -->
# Citation stripping & score extraction — how do you remove grounded citations from evidence and read a 0-10 relevance score out of free text?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** What exact regex removes author-year citations from evidence summaries without eating content, and what fallback ladder recovers an integer relevance score when the model formats it unpredictably?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/utils.py:strip_citations` (:127-131) and `extract_score` (:134-167); consumed by `core._map_fxn_summary` :357-359 (post-summary strip unless `answer.skip_evidence_citation_strip`) and :317-349 (score extraction on every parser path).
**Signature:** `def strip_citations(text: str) -> str`; `def extract_score(text: str) -> int` (0 = sentinel "not applicable", 1-10 otherwise).
**Data Shape:** Free LLM text in; stripped text / small int out; `extract_score` raises ValueError when no signal exists (caller wraps into retryable `LLMBadContextJSONError`).

### Decisive source
```python
citation_regex = r"\b[\w\-]+\set\sal\.\s\([0-9]{4}\)|\((?:[^\)]*?[a-zA-Z][^\)]*?[0-9]{4}[^\)]*?)\)"
return re.sub(citation_regex, "", text, flags=re.MULTILINE)

def extract_score(text):
    last_line = text.rsplit("\n", maxsplit=1)[-1]
    if "n/a" in last_line.lower() or "not applicable" in text.lower() \
       or "not relevant" in text.lower(): return 0
    score = re.search(r"[sS]core[:is\s]+([0-9]+)", text)      # "Score: 8"
    if not score: score = re.search(r"\(([0-9])\w*\/", text)  # "(8/"
    if not score: score = re.search(r"([0-9]+)\w*\/", text)   # "8/"
    if score:
        s = int(score.group(1))
        if s > 10: s = int(s / 10)   # sometimes becomes out of 100
        return s
    scores = re.findall(r"([0-9]+)", text[-15:])              # last-resort tail digits
    ...
```

**Flow:** Score ladder: N/A sentinel (last line OR anywhere phrase) → `Score:` prefix → parenthesized fraction → bare fraction → last-15-chars digit scan. Stripping happens AFTER parsing so the score line survives parsing, THEN citations are removed so the answer LLM never sees evidence-internal citations that would collide with `pqac-*` keys.
**Invariant:** A parenthetical counts as a citation ONLY if it contains both a letter and a 4-digit year — `(Smith 199)` style malformed cites survive (pinned by test_malformed_citations); `NA` alone is NOT a sentinel (gene names contain "NA").
**Probe:** `tests/test_paperqa.py:133-191` (nine strip_citations cases incl. commas/pages/no-space) and `:291-314` (extract_score incl. sentinel→0, Score:→8); executed lifted probes T1a-T1c/T2a-T2c GREEN byte-exact.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "strip_citations extract_score", limit: 10 });
// SEMANTICALLY_RELATED edges cluster the nine citation-strip unit tests around utils.strip_citations
```

## Verdict
Adopt both ladders as-is — they encode months of observed LLM formatting failures; adapt the >10÷10 heuristic if your scores are never x/100; omit the last-15-char digit scan only if your parser guarantees structured output. Direct tests upstream pin both; lifted probes executed GREEN.
