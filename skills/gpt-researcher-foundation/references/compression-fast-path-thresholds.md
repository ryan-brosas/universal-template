<!-- capsule-v2 -->
# Compression fast-path thresholds — when is the whole embedding pipeline skipped, and what runs when it isn't?

**Source:** gpt-researcher Apache-2.0 `main@5d84d2f5553e70a2765a8ff3a0d2672d60437ce8`; Codebase Memory `gpt-researcher`. **Question:** Under what conditions does context compression reduce to a plain passthrough, and what are the exact split/filter parameters when it doesn't?

## ContextCompressor dual path
**Path/Symbol:** `gpt_researcher/context/compression.py:148-188` (`async_get_context`), `:127-146` (`__get_contextual_retriever`), WrittenContentCompressor twin `:191-265`.
**Signature:** `async def async_get_context(self, query: str, max_results: int = 5, cost_callback=None) -> str`
**Data Shape:** Thresholds from env with defaults: `COMPRESSION_THRESHOLD=8000` chars total; `SIMILARITY_THRESHOLD=0.35`. Pipeline = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100) → EmbeddingsFilter(similarity_threshold) inside DocumentCompressorPipeline over SearchAPIRetriever.

### Decisive source
```python
total_chars = sum(len(str(doc.get('raw_content', ''))) for doc in self.documents)
chunk_threshold = int(os.environ.get("COMPRESSION_THRESHOLD", "8000"))
if total_chars < chunk_threshold and len(self.documents) <= max_results:
    # Fast path: map scraper keys into metadata pretty_print_docs expects.
    direct_docs = [Document(page_content=doc.get('raw_content', '') or '',
                            metadata={"title": doc.get("title", "") or "",
                                      "source": doc.get("source") or doc.get("url") or ""})
                   for doc in self.documents[:max_results]]
    return self.prompt_family.pretty_print_docs(direct_docs, max_results)
```

**Flow:** small-input gate (chars AND count must BOTH pass) → direct Document mapping preserving order → else estimate+report embedding cost and run the compressor in a worker thread (`asyncio.to_thread`) → `pretty_print_docs(relevant_docs, max_results)`.
**Invariant:** fast path MUST remap `url` → `source` (downstream citation formatting reads metadata["source"]) and coerce None raw_content before slicing. WrittenContentCompressor is the section-keyed twin (`SectionRetriever`, metadata key `section_title`, returns formatted list not string). VectorstoreCompressor has NO splitter — it trusts store-side chunking.
**Probe:** `tests/test_context_compressor_source_url.py` pins url→source mapping AND explicit-source preference on the fast path; battery P10a-c GREEN (threshold defaults ×1 each).
