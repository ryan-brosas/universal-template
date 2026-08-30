<!-- capsule-v2 -->
# Snippet retrieval & dedup — how does the information table serve per-section evidence, and why does the argsort direction look backwards?

**Source:** storm MIT `main@fb951af7`; Codebase Memory `storm`. **Question:** How are (url, snippet) pairs indexed once and retrieved top-k per query with URL-level dedup?

## Connected graph-selected seam
**Path/Symbol:** `knowledge_storm/storm_wiki/modules/storm_dataclass.py:StormInformationTable` (:48-145) — `construct_url_to_info`, `prepare_table_for_retrieval`, `retrieve_information`.
**Signature:** `prepare_table_for_retrieval()`; `retrieve_information(queries: Union[List[str], str], search_top_k: int) -> List[Information]`.
**Data Shape:** Flat parallel arrays `collected_urls[i] ↔ collected_snippets[i]` (one row PER SNIPPET, not per url) + sentence-transformer matrix `encoded_snippets`; returns Information clones whose `.snippets` hold only the selected strings.

### Decisive source
```python
# build: first URL wins the object; later snippets EXTEND it; then global set-dedup
if storm_info.url in url_to_info:
    url_to_info[storm_info.url].snippets.extend(storm_info.snippets)
else:
    url_to_info[storm_info.url] = storm_info
for url in url_to_info:
    url_to_info[url].snippets = list(set(url_to_info[url].snippets))

# retrieve: ASCENDING argsort + tail slice = descending top-k WITHOUT a sort of the rest
sim = cosine_similarity([encoded_query], self.encoded_snippets)[0]
sorted_indices = np.argsort(sim)
for i in sorted_indices[-search_top_k:][::-1]:
    selected_urls.append(self.collected_urls[i]); selected_snippets.append(self.collected_snippets[i])
...
selected_url_to_info[url] = copy.deepcopy(self.url_to_info[url])   # clone before narrowing
selected_url_to_info[url].snippets = list(url_to_snippets[url])    # set -> list
```

**Flow:** After research, all turns' results fold into one url→Information map (snippets unioned) → at article time, snippets flatten to parallel arrays and embed ONCE → each section's query list retrieves top-k snippet rows per query → selections group by url into a SET → deep-cloned Information per selected url carries ONLY its selected snippets to the writer.
**Invariant:** (1) The array index is the join key between url and snippet — any re-sort of one array without the other corrupts attribution. (2) Deep-copy before narrowing or you truncate the master table's snippets for everyone. (3) Per-query top-k means a url can be selected by several queries; the url-set dedup keeps one entry but UNIONED snippets. (4) Encoder is loaded INSIDE `prepare_table_for_retrieval` (`paraphrase-MiniLM-L6-v2`) — local model download is an article-stage dependency, not a research-stage one.
**Probe:** deterministic pin GREEN — storm_dataclass.py:128-132 ascending-argsort tail-slice byte-verified this pass.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "storm", query: "retrieve_information search_top_k prepare_table_for_retrieval", limit: 10 });
```

## Verdict
Adopt flat-parallel-array embedding + argsort-tail top-k + clone-then-narrow as a compact local RAG retriever; adapt the encoder model; omit the set-based snippet dedup where snippet order matters. Caveat: no upstream tests; source-pinned.
