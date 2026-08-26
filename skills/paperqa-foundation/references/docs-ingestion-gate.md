<!-- capsule-v2 -->
# Docs ingestion gate — what must pass before a file becomes Doc + Texts, and when is identity upgraded to DocDetails?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** Trace `Docs.aadd` end-to-end: citation inference, DOI/title extraction, metadata upgrade, validity rejection, and dedupe-by-dockey — in what order and with which fallbacks?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/docs.py:Docs.aadd` (:156-338), `aadd_texts` (:340-401), `_get_unique_name` (:84-91), `retrieve_texts`/`aget_evidence` (:456-586), `aquery` (:588-721).
**Signature:** `async def aadd(self, path, citation=None, docname=None, dockey=None, title=None, doi=None, authors=None, settings=None, ...) -> str | None` (None = already present / filtered).
**Data Shape:** dockey defaults to md5(content); citation None ⇒ LLM call on first chunk (pages 1-3 peek) with degenerate-output fallback `"Unknown, {basename}, {year}"` when len<3 or contains "Unknown"/"insufficient".

### Decisive source
```python
if (doi is title is None) and parse_config.use_doc_details:
    result = await llm_model.call_single(messages=[...structured_citation_prompt.format(citation=citation)])
    clean_text = cast("str", result.text).split("{", 1)[-1].split("}", 1)[0]   # isolate first{..last}
    clean_text = "{" + clean_text + "}"
    try: citation_json = json.loads(clean_text)  # title/doi/authors extracted; JSONDecodeError+AttributeError → warn-and-continue
...
doc = await metadata_client.upgrade_doc_to_doc_details(doc, **(query_kwargs | kwargs))
...
if await self.aadd_texts(texts, doc, all_settings, embedding_model): return doc.docname
return None    # duplicate dockey OR doc_filters reject
```
Validity gate before accepting (:313-335): non-empty texts, ≥10 chars first chunk, ≥20 chars de-newlined first-two chunks, maybe_is_text over first five — unless `disable_doc_valid_check`. Deletion bookkeeping: `deleted_dockeys` retained so retrieval pads k by `len(deleted_dockeys)` then filters (:476-490).

**Flow:** aadd_texts short-circuits on existing dockey BEFORE embedding (cost guard), applies doc_filters with `!`-negation/`?`-optional key grammar, embeds only if `texts[0].embedding is None`, renames texts if docname collided, defers index insertion to retrieval time ("we defer adding texts to the texts index to retrieval time" :394-395).
**Invariant:** Adding is IDEMPOTENT per content-hash dockey; the deferred index means `docs.texts` grows without vector-store writes until first query; deleted docs still count toward fetch_k padding so top-k stays honest.
**Probe:** `tests/test_paperqa.py::test_nonduplicate_contexts` (:844), evidence path of `::test_json_evidence` (:875); agents-side ingestion via `process_file` pins manifest-driven adds.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "aadd_texts deleted_dockeys _build_texts_index retrieve_texts", limit: 10 });
// trace_path --function-name aadd --direction inbound → agents.search.process_file, CLI
```

## Verdict
Adopt ingest-order (peek-citation → structured-extract → metadata upgrade → validity → idempotent add); adapt the LLM citation prompt to your domain; omit multimodal plumbing for text-only corpora. Coverage: all cited paths no_recorded_issue at pinned HEAD.
