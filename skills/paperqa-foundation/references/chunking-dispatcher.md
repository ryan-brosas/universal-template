<!-- capsule-v2 -->
# Chunking dispatcher — which chunker runs for which extension, and what do page-span chunk names guarantee?

**Source:** paper-qa (Apache-2.0) `main@57e89f72`; Codebase Memory `ext-paper-qa`. **Question:** Given any input file, how does read_doc choose a parser + chunker pair, and why do PDF chunks carry page ranges in their names while text chunks say "chunk N"?

## Connected graph-selected seam
**Path/Symbol:** `src/paperqa/readers.py:read_doc` (:426-557) dispatching to `chunk_pdf` (:105-143), `chunk_text` (:258-315), `chunk_code_text` (:318-358), `_make_chunk` (:92-102); `resolve_page_range` (:58-66).
**Signature:** `async def read_doc(path, doc, parsed_text_only=False, include_metadata=False, chunk_chars=5000, overlap=250, multimodal_enricher=None, parse_pdf=None, **parser_kwargs)`.
**Data Shape:** Extension→parser map: `.pdf`→injected parse_pdf (REQUIRED — ValueError if None; sync fns run inline "Some PDF parsers are not thread-safe"), `.txt`/`.html`→parse_text (to_thread; html via html2text), images→parse_image (media-only, zero text), office→parse_office_doc, else→split_lines fallback. ChunkMetadata.name embeds the full reproducibility fingerprint: `paper-qa={ver}|algorithm={kind}|reduction=cl100k_base|size=N|overlap=M{enrichment_summary}`.

### Decisive source
```python
# chunk_pdf: page-boundary aware
while len(split) > chunk_chars:
    texts.append(_make_chunk(parsed_text, doc, split[:chunk_chars], pages[0], pages[-1]))
    split = split[chunk_chars - overlap:]      # overlap CARRIES into next chunk
    pages = [page_num]                          # span restarts at current page
...
if len(split) > overlap or not texts:           # tail kept only if meaningful OR nothing yet
# chunk_text: token-aware sizing
char_count = parsed_text.metadata.total_parsed_text_length
token_count = len(content)                      # cl100k_base tokens
chars_per_token = char_count / token_count      # e.g. 5.5 → chunk_tokens = chunk_chars / cpt
```

**Flow:** PDFs chunk per-page accumulation with names `{docname} pages 1-3`; plain text encodes to tiktoken FIRST then cuts at computed token boundaries (`{docname} chunk {i+1}`); code splits by lines (`lines {a}-{b}`). Enrichment runs on the WHOLE parsed text BEFORE chunking so descriptions can span pages. `chunk_chars == 0` ⇒ single no-chunk Text.
**Invariant:** Chunk names are load-bearing retrieval metadata — the agent's search index and evidence display assume page spans are real; ImpossibleParsingError (empty parse) aborts loudly instead of indexing silence; media attach to the chunk covering their page range.
**Probe:** `tests/test_paperqa.py::test_pdf_reader_w_no_chunks` (:1584), `::test_chunk_metadata_reader` (:1793); executed lifted probes T8a-T8c GREEN (page-span naming across boundary + overlap carry byte-exact).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-paper-qa", query: "read_doc chunk_pdf chunk_text ChunkMetadata", limit: 10 });
```

## Verdict
Adopt extension-dispatch + page-span naming + tail-keep rule; adapt parser injection to your PDF backend (pymupdf/pypdf/docling plugins are separate packages here); omit office/image parsers if your corpus is PDF-only. Probes executed GREEN.
