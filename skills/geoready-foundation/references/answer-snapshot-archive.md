<!-- capsule-v2 -->
# Answer snapshot archive — citation extraction from AI answer text with normalized timestamps

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you persist full AI answers + their citations so later passes can measure share-of-voice?

## URL regex extraction, position-preserving dedupe, two-table SQLite
**Path/Symbol:** `src/geo_optimizer/core/snapshots.py:extract_citations` (60–79), `_citation_from_url` (49–58), `_normalize_timestamp` (17–34), `SnapshotStore._init_db` (96+).
**Signature:** `extract_citations(answer_text: str, extra_urls: list[str] | None = None) -> list[AnswerCitation]`.
**Data Shape:** `AnswerCitation(url, position 1-based, domain lowercase)`; tables `answer_snapshots(query_text, prompt_text, model_name, provider_name, answer_text, recorded_at)` + child `answer_snapshot_citations(snapshot_id FK CASCADE, url, domain, position)`.

### Decisive source
```python
_URL_RE = re.compile(r"https?://[^\s<>\"']+")

def _citation_from_url(url: str, position: int) -> AnswerCitation:
    cleaned = url.rstrip(").,;]")          # sentence punctuation glued to the URL
    parsed = urlparse(cleaned)
    return AnswerCitation(url=cleaned, position=position, domain=(parsed.hostname or "").lower())
...
for index, match in enumerate(_URL_RE.finditer(answer_text), start=1):
    citation = _citation_from_url(match.group(0), index)
    if citation.url in seen: continue      # dedupe keeps FIRST position
    seen.add(citation.url); citations.append(citation)
# extra_urls appended AFTER text matches, also deduped, positions continue
```

**Flow:** timestamp normalization coerces date-only strings to midnight UTC, `Z` suffix to `+00:00`, naive datetimes get UTC — unparseable values pass through unchanged rather than raising; store saves snapshot row then citations with cascade delete; archive queries filter by domain/date with `DEFAULT_SNAPSHOT_LIMIT=20`.
**Invariant:** Position = order of first appearance in the ANSWER (share-of-voice metric depends on it), and punctuation stripping must not eat legitimate trailing chars beyond `).,;]`. The two-table split (snapshot 1↔N citations) is what makes per-domain aggregation queries possible without parsing stored text again.
**Probe:** `tests/test_snapshots.py::test_extract_citations_positions_and_dedupe` (+ store round-trips; `PYTHONPATH=src pytest tests/test_snapshots.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "extract_citations snapshot store", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt first-position dedupe + tolerant timestamp normalization for any answer/citation archiver; adapt schema fields; omit SQLite if you already have a store.
