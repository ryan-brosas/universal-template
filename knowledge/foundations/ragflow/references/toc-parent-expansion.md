<!-- capsule-v2 -->
# toc-parent-expansion — how do TOC hits and child chunks pull in their parents?

**Source:** ragflow Apache-2.0 `main@9ea83b7a9d003d948fe4c99c6f35de02115a96e8`; Codebase Memory `ext-ragflow`. **Question:** What are the exact merge rules when secondary retrieval surfaces structural relatives of matched chunks?

## retrieval_by_toc / retrieval_by_children merge contracts
**Path/Symbol:** `Dealer.retrieval_by_toc` `rag/nlp/search.py:883-944`; `Dealer.retrieval_by_children` `:946-1000`.
**Signature:** `retrieval_by_toc(query, chunks, tenant_ids, chat_mdl, topn=6)`; `retrieval_by_children(chunks, tenant_ids) -> list`.
**Data Shape:** parent links ride `mom_id`; TOC chunks are rows with `"toc_kwd": "toc"` holding a JSON list in content_with_weight; synthetic vectors are `[0.0]*1024` placeholders unless a real `_vec` key exists on the fetched row.

### Decisive source
```python
# children: pop children out, then either fall back or synthesize ONE parent doc
mom_chunks[ck["mom_id"]].append(chunks.pop(i))
...
chunk = self.dataStore.get(id, idx_nms[0], [ck["kb_id"] for ck in cks])
if chunk is None:
    logging.warning("Parent chunk '%s' not found in the index; falling back to %d child chunk(s).", ...)
    chunks.extend(cks); continue
...
"similarity": np.mean([ck["similarity"] for ck in cks]),
# toc: LLM picks section ids over the doc's stored TOC; new chunks join, all re-sort
chunks[id2idx[cid]]["similarity"] += sim      # existing chunk: ADDITIVE boost
...
return sorted(chunks, key=lambda x: x["similarity"] * -1)[:topn]
```

**Flow:** children plane: partition by mom_id (pop-in-place while iterating with manual index), fetch each parent once across ALL its children's kb_ids, missing parent → warn + keep children untouched, found → replace N children with one synthesized doc whose content_ltks joins child texts, important_kwd unions, similarity MEANS. TOC plane: pick top doc by summed similarity, load ≤128 TOC rows, LLM ranks topn*2 sections, existing chunks get similarity INCREMENT, brand-new ids get full chunk dicts with vector placeholder discovered from any `*_vec` key.
**Invariant:** both functions re-sort descending at return; neither mutates the input ordering before its own partition pass completes safely (children uses explicit `i` control because `pop` shifts indices). Placeholder vectors mark synthesized docs so downstream citation embedding sees zero vectors rather than crashing.
**Probe:** `grep -n 'def retrieval_by_toc\|def retrieval_by_children' rag/nlp/search.py` → :883/:946; `sed -n '970,971p' rag/nlp/search.py | grep -c 'falling back to'` → 1; `grep -n '"similarity": np.mean(\[ck\["similarity"\]' rag/nlp/search.py` → 1 hit :986. Executed GREEN at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ragflow", query: "retrieval_by_children mom_id parent chunk fallback", limit: 5, fields: ["name", "file"] });
```

## Verdict
Adopt mean-of-children synthesis and additive TOC boosts; adapt the LLM TOC selector prompt boundary (import lives in rag.prompts.generator, lazy to dodge circular import); omit placeholder-vector plumbing only if your pipeline never embeds synthesized rows.
