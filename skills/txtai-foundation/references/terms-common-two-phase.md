<!-- capsule-v2 -->
# Terms common-terms two-phase scorer — how does a term-at-a-time BM25 engine stay fast when a query hits very common terms?

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must a postings-list scorer handle terms that appear in >10% of documents without scanning every document?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/scoring/terms.py:Terms.search` (:164-215), `.topn` (:482-514), `.merge` (:516-543), `.candidates` (:545-561), `.weights` (:457-480).
**Signature:** `search(terms, limit)` → `[(id, score)]`; internal `scores = np.zeros(len(self.ids), np.float32)`.
**Data Shape:** per-term posting = `(uids array("q"), freqs array("q"))` cached in SQLite blobs (term PRIMARY KEY, little-endian byteswapped on big-endian hosts); `weights()` memoized via `functools.lru_cache(maxsize=500)`.

### Decisive source
```python
# Score less common terms
terms, skipped, hasscores = Counter(terms), {}, False
for term, freq in terms.items():
    # Compute or lookup term weights
    uids, weights = self.weights(term)
    if uids is not None:
        # Term considered common if it appears in more than 10% of index
        if len(uids) <= self.cutoff * len(self.ids):
            scores[uids] += freq * weights
            hasscores = True
        else:
            skipped[term] = freq

# Merge in common term scores and return top n matches
return self.topn(scores, limit, hasscores, skipped)
```
```python
# topn: candidates sized smaller of limit*5 / index size, computed BEFORE merging common terms
topn = min(len(scores), limit * 5)
matches = self.candidates(scores, topn)
self.merge(scores, matches, hasscores, skipped)
if not hasscores:
    matches = self.candidates(scores, topn)
```

**Flow:** expand wildcards (`*`→`%` LIKE, escaped literal `*` as `__asterisk__`) under RLock → score terms appearing in ≤ cutoff (default 0.1) of docs directly into the dense scores array → take top `limit*5` candidates → merge COMMON (skipped) terms but only for those candidate ids (`np.searchsorted` against the sorted posting uids; requires posting uids sorted — they are, by construction of insert order) → recompute candidates if NOTHING scored → argpartition + reorder by `-scores`, filter score>0.

**Invariant:** The two-phase split mirrors Lucene's common-terms query: correctness depends on merge being restricted to the pre-candidate set when partial scores exist (score shifting among candidates is allowed); when NO term scored (`hasscores=False`) the merge runs over ALL docs and candidates are recomputed after. Deletes are zeroed inside `candidates()` (`scores[self.deletes] = 0`) so tombstoned docs can never re-enter via merge.

**Probe:** `test/python/testscoring/testkeyword.py:testTermsEmpty` (:135-148 — empty index and never-initialized cursor both return [] not crash), `testDeleteUnknownId` (:150-166 — deleting unknown id is no-op).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "Terms topn candidates merge cutoff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ≤cutoff direct-score / common-term candidate-restricted merge ladder with the recompute-on-empty fallback; adapt cutoff (0.1) and candidate multiplier (5×limit); omit SQLite blob storage if you have an existing postings store. Coverage caveat: pinned by testkeyword integration tests rather than a dedicated unit file.
