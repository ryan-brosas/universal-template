<!-- capsule-v2 -->
# BM25/TFIDF scoring ladder — where do the stats live and when are they frozen?

**Source:** txtai Apache-2.0 `main@a10667a` (9.13.0); Codebase Memory `ext-txtai`. **Question:** How must BM25/TFIDF document statistics be accumulated, finalized, and reused so scores stay consistent between index and query time?

## Connected graph-selected seam
**Path/Symbol:** `src/python/txtai/scoring/tfidf.py:TFIDF.index` (:103-134), `.weights` (:136-159), `.computeidf/.score`; `src/python/txtai/scoring/bm25.py:BM25.computeidf/.score` (:25-32).
**Signature:** `index(documents=None)` finalizes; `score(freq, idf, length)` vectorized over numpy arrays.
**Data Shape:** Counters `docfreq` (docs containing term), `wordfreq` (total occurrences), `tags`; scalars `total`, `tokens`, `avgdl`, `avgfreq`, `avgidf`, `avgscore`; `self.idf {term: float}`.

### Decisive source
```python
# TFIDF.index — finalize after all inserts
self.tokens = sum(self.wordfreq.values())
self.avgfreq = self.tokens / len(self.wordfreq.values())
self.avgdl = self.tokens / self.total
idfs = self.computeidf(np.array(list(self.docfreq.values())))
for x, word in enumerate(self.docfreq):
    self.idf[word] = float(idfs[x])
self.avgidf = float(np.mean(idfs))
self.avgscore = self.score(self.avgfreq, self.avgidf, self.avgdl)
```
```python
# BM25
def computeidf(self, freq):
    return np.log(1 + (self.total - freq + 0.5) / (freq + 0.5))

def score(self, freq, idf, length):
    k = self.k1 * ((1 - self.b) + self.b * length / self.avgdl)
    return idf * (freq * (self.k1 + 1)) / (freq + k)
```
```python
# weights(): unknown tokens fall back to avgidf, tag tokens boosted to max weight
idf = np.array([self.idf[token] if token in self.idf else self.avgidf for token in tokens])
```

**Flow:** insert accumulates ONLY counters (`addstats`: wordfreq update per occurrence, docfreq update per unique set(tokens), total += 1) → `index()` freezes ALL derived stats at once (avgdl, idf table, avgidf, avgscore used later as the default-normalization anchor) → search path uses the frozen `self.idf` dict; OOV query tokens get `avgidf`, never a KeyError.

**Invariant:** IDF is computed from `docfreq` (document frequency), NOT wordfreq — confusing the two Counters is the classic wrong port. Stats freeze means upserts that only insert documents without calling `index()` score against stale statistics; tag boost lifts tag-token weights to the max weight in the list (:151-157), gated on tags appearing in ≥0.5% of docs.

**Probe:** `test/python/testscoring/testkeyword.py:testBM25` (:38-44) and `testTFIDF` (:169+ via shared runTests matrix); normalization twins at :356-398 pin `avgscore`-anchored default normalization and bayes/bb25 aliases.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-txtai", query: "BM25 computeidf avgdl docfreq avgscore", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt counter-then-freeze stat lifecycle + docfreq-vs-wordfreq distinction + OOV→avgidf fallback; adapt k1/b defaults (1.2/0.75); omit tag boosting if you carry no tags. Coverage caveat: exercised through ScoringFactory integration tests.
