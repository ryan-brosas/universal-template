<!-- capsule-v2 -->
# Counted vocabulary growth — how should search keywords be invented without an LLM minting prose?

**Source:** OpenOutreach GPL-3.0 `main@c3ac1434118ac5301b193506d1d01e6e313bc622`; Codebase Memory `openoutreach`. **Question:** Where do new query tokens come from after cold start, and what keeps a token in the right searchable field?

## Connected graph-selected seam
**Path/Symbol:** `openoutreach/core/pipeline/vocabulary.py:refresh` (:99-140), `tokenize` (:52-59), `seed_seniorities` (:143-160), `_qualified_source_fields` (:76-96).
**Signature:** `refresh(campaign) -> int` (tokens added); `tokenize(text) -> set[str]`; `admitted_keywords() -> sorted list[(field, token)]`.
**Data Shape:** keyword = one word per `(field, token)` pair; admission = document frequency ≥ `MIN_DOCUMENT_FREQUENCY = 2` over qualified profiles.

### Decisive source
```python
_TOKEN = re.compile(r"[a-z][a-z0-9&/+.\\-]{1,}")   # letters/digits + title punctuation:
                                                   # ai-native, ai/ml, co-founder, r&d
def tokenize(text):
    return {t for t in _TOKEN.findall(text.lower()) if t not in ENGLISH_STOP_WORDS}

# refresh(): df per (field, token) — how many QUALIFIED profiles carry it, per source field:
for search_field, row_keys in KEYWORD_SOURCE_FIELDS.items():
    text = " ".join(str(fields.get(k) or "") for k in row_keys)
    for token in tokenize(text):
        frequency[(search_field, token)] = frequency.get(...) + 1
admitted = [pair for pair, df in frequency.items() if df >= MIN_DOCUMENT_FREQUENCY]
```

**Flow:** every discovery pass → collect qualified leads' per-field raw text → tokenize per axis → admit at df≥2 → insert unseen pairs → frontier re-expands FIRED nodes with the grown vocabulary (new tokens are only ever children of already-fired nodes).
**Invariant:** Growth is counting, not generation — the old engine asked an LLM to invent clause values and got prose ("Head of Content Strategy") where every word is another AND, a large independent cause of 60 consecutive empty queries. A token's field is **measured, not chosen**: `cto` is alive in lead_job_title and dead elsewhere, `belgium` the reverse; reading each axis from the row fields that ARE that axis (`discovery.KEYWORD_SOURCE_FIELDS`) keeps vocabularies nearly disjoint for free. The df≥2 floor drops 65% of tokens (3,485→1,208) losing zero good ones until df≥10 — the singleton tail is mostly company names/typos AND is 56% of the top of any embedding ranking, so it would fire first. There is no cadence knob: recounting is cheaper than remembering when you last did.
**Probe:** `tests/test_discovery.py::TestSeedKeywords` (:229+), `tests/test_discovery.py::TestSeniorityVocabulary` (:22-42).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openoutreach", query: "refresh vocabulary", limit: 5 });
```

## Verdict
Adopt counted-from-accepted-items vocabulary with df floor; adopt measured field assignment via source-field mapping; adopt closed-vocabulary seeding for provider-published axes (`lead_seniority` seeded whole from the Literal — an out-of-list value isn't an error but an empty page). Adapt stopword source (sklearn's list — no NLP dependency) and regex to your domain text; omit the Dunning log-likelihood upgrade note unless your tail needs a sharper cut.
