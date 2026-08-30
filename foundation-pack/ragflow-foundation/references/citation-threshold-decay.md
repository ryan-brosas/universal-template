<!-- capsule-v2 -->
# citation-threshold-decay — how are inline [ID:n] citations attached to answer sentences?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** How does insert_citations decide which chunks cite which sentence, and when does it give up?

## Decaying-similarity citation attach
**Path/Symbol:** `Dealer.insert_citations` `rag/nlp/search.py:283-360`.
**Signature:** `insert_citations(answer, chunks, chunk_v, embd_mdl, tkweight=0.1, vtweight=0.9)` → `(res: str, seted: set[str])`.
**Data Shape:** sentence split via `re.split(r"([^\|][；。？!！،؛؟۔\n]|[a-z\u0600-\u06FF][.?;!،؛؟][ \n])", ...)` — Arabic punctuation classes included; pieces <5 chars dropped from matching (`idx` list maps back to original positions).

### Decisive source
```python
thr = 0.63
while thr > 0.3 and len(cites.keys()) == 0 and pieces_ and chunks_tks:
    for i, a in enumerate(pieces_):
        sim, tksim, vtsim = self.qryr.hybrid_similarity(ans_v[i], chunk_v, ..., tkweight, vtweight)
        mx = np.max(sim) * 0.99
        if mx < thr:
            continue
        cites[idx[i]] = list(set([str(ii) for ii in range(len(chunk_v)) if sim[ii] > mx]))[:4]
    thr *= 0.8
...
for c in cites[i]:
    res += f" [ID:{c}]"
```

**Flow:** split answer into sentences (fenced code blocks preserved intact via ``` pairing) → embed sentences once → per piece compute hybrid similarity against all chunk vectors → attach top-≤4 chunk ids above the relative bar `max*0.99` when it clears the absolute threshold → decay threshold ×0.8 per pass until any citation lands or floor 0.3 → reassemble inserting `[ID:c]` after each cited piece, deduped across the whole answer via `seted`.
**Invariant:** dimension-mismatch guard zero-fills mismatched `chunk_v[i]` BEFORE asserting equality (`len(ans_v[0]) != len(chunk_v[i])` → replace + warning) so one stale-dim chunk cannot crash the whole answer. The loop continues ONLY while no citations exist — first success freezes later pieces' chances at higher thresholds.
**Probe:** `grep -n 'thr = 0.63' rag/nlp/search.py` → 1 (:333); `grep -n 'thr \*= 0.8' rag/nlp/search.py` → 1 (:342); `grep -n 'sim\[ii\] > mx' rag/nlp/search.py` → 1 (:341); `grep -n 'np.max(sim) \* 0.99' rag/nlp/search.py` → 1 (:337). All executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "insert_citations threshold decay citations", limit: 5, fields: ["signature", "file"] });
```

## Verdict
Adopt the decay ladder + relative-bar semantics + ≤4-cite cap; adapt the multilingual sentence regex to your locale set; omit the code-fence passthrough only if your answers never contain fenced blocks (risky).
