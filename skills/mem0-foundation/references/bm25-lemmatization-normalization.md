<!-- capsule-v2 -->
# BM25 text normalization — how does write-time lemmatization keep keyword recall without over-stemming?

**Source:** mem0 MIT `main@8d5b7865`; Codebase Memory `mem0`. **Question:** what exact token stream is materialized into `text_lemmatized` at insert (and recomputed on update), and why does the -ing form survive alongside its lemma?

## Connected graph-selected seam
**Path/Symbol:** `mem0/utils/lemmatization.py` `lemmatize_for_bm25` (:22-50); shared loader `mem0/utils/spacy_models.py` (`get_nlp_lemma` :68-91, `get_nlp_full` :48-66, module latch/lock state :14-18); consumers: `_create_memory` (`text_lemmatized` :1976) and `_update_memory` (:2011, recompute on TEXT change only — per update-ladder capsule); query side `utils/scoring.py get_bm25_params` lemmatizes the QUERY with the same function.
**Signature:** `lemmatize_for_bm25(text: str) -> str`; `get_nlp_lemma() -> Optional[spacy.Language]` (lemma-only model, ner+parser disabled).
**Data Shape:** output = space-joined lowercase alnum lemma tokens, stop words and punctuation dropped, PLUS original `-ing` tokens when they differ from their lemma; empty string in → empty string out; spaCy unavailable → original text unchanged.

### Decisive source
```python
doc = nlp(text.lower())
for token in doc:
    if token.is_punct or token.is_stop:
        continue
    lemma = token.lemma_
    if lemma.isalnum():
        tokens.append(lemma)
    # Also add original if it ends in -ing and differs from lemma.
    # This handles noun/verb ambiguity (meeting/meet, attending/attend).
    if token.text.endswith("ing") and token.text != lemma and token.text.isalnum():
        tokens.append(token.text)
```
```python
# spacy_models.py — one shared model instance for entity_extraction AND lemmatization,
# with a permanent failure latch so a broken install costs ONE load attempt per process
if _load_failed_lemma:
    return None            # fast-path latch: never re-attempt after failure
if _nlp_lemma is not None:
    return _nlp_lemma
with _lock:                # double-checked locking around the (possibly downloading) load
    if _nlp_lemma is not None: return _nlp_lemma
    if _load_failed_lemma: return None
    try:
        _ensure_model_available()          # auto-download en_core_web_sm if missing
        _nlp_lemma = spacy.load("en_core_web_sm", disable=["ner", "parser"])
    except Exception as e:
        logger.warning(...); _load_failed_lemma = True
        return None                        # fail-open: BM25 falls back to raw text
```

**Flow:** write path embeds and stores `lemmatize_for_bm25(data)` as payload field `text_lemmatized` alongside the vector → update path recomputes it ONLY when text changed (metadata-only updates keep the stale value deliberately — bm25-write-path capsule's documented tradeoff) → search path lemmatizes the incoming query with the same pipeline before BM25 scoring, and `get_bm25_params` derives sigmoid parameters FROM the lemmatized query's term count.
**Invariant:** the -ing dual-token rule is the recall trick: spaCy lemmatizes context-dependently ("meeting" the noun stays "meeting", the verb becomes "meet") so keeping BOTH forms makes noun-vs-verb queries match regardless of the writer's intent; loader failures are latched PER MODEL VARIANT (full vs lemma have separate flags) and fail OPEN to unlemmatized text — a port that raises here takes down all memory writes when spaCy is missing; lowering happens BEFORE analysis so store-side and query-side streams agree.
**Probe:** `tests/utils/test_lemmatization.py::test_ing_preservation` (asserts "attending" or "attend" present), `::test_verb_forms_normalized` (asserts "meeting" kept alongside "attend"), `::test_empty_string` ("" → ""), plus lowercasing/punctuation tests; suite auto-skips when the spaCy model is absent (fixture `_ensure_spacy`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-mem0", query: "remove_code_blocks lemmatize_for_bm25", limit: 10, fields: ["signature", "name", "file"] });
```
(resolved: mnt-hdd-utopia-inspo-memory-mem0.mem0.utils.lemmatization.lemmatize_for_bm25 Function mem0/utils/lemmatization.py 22-50)

## Verdict
Adopt the dual-token -ing rule + fail-open latch pattern; adapt the NLP backend (any lemmatizer works if query and document sides share it); omit nothing on the write side — recomputing on metadata-only updates would silently corrupt the stale-BM25 tradeoff.
