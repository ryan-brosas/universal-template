<!-- capsule-v2 -->
# Structure-aware markdown chunking — how do you split a page's markdown for LLM consumption without destroying tables, code fences, or lists?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how does chunking keep char offsets exact across chunks and carry table headers forward over multi-chunk tables?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/dom/markdown_extractor.py` — `_BlockType`/`_AtomicBlock` (:233), `_parse_atomic_blocks` (:262), `chunk_markdown_by_structure` (:411), `_preprocess_markdown_content` (:148), `extract_clean_markdown` (:21), `convert_html_to_markdown` (:110).
**Signature:** `chunk_markdown_by_structure(content: str, max_chunk_chars: int = 100_000, overlap_lines: int = 5, start_from_char: int = 0) -> list[MarkdownChunk]`.

### Decisive source
```python
# Phase 1 atomic blocks: BLANK | HEADER | CODE_FENCE (consumed to closing fence)
#   | TABLE (header+separator ONE block; each data row its own) | LIST_ITEM
#   (item + indented/blank continuations) | PARAGRAPH (to next blank or block opener)
# Offset bookkeeping: +1 per line for the split newline, then a trailing fix:
if blocks and content and blocks[-1].char_end > len(content):
    blocks[-1] = _AtomicBlock(..., char_end=len(content))  # parser overshoot on trailing \n

# Phase 2 greedy assembly with header-preferred splitting:
if current_size + block_size > max_chunk_chars and current_chunk:
    best_split = len(current_chunk)
    for j in range(len(current_chunk) - 1, 0, -1):        # scan BACKWARDS for last HEADER
        if current_chunk[j].block_type == _BlockType.HEADER:
            prefix_size = sum(b.char_end - b.char_start for b in current_chunk[:j])
            if prefix_size >= max_chunk_chars * 0.5:      # never create tiny chunks
                best_split = j; break
    raw_chunks.append(current_chunk[:best_split])
    current_chunk = current_chunk[best_split:]            # carried blocks start next chunk

# Phase 3 overlap: table continuation => header lines FIRST (dedup vs trailing),
# else last N lines of previous chunk. Header tracking persists across chunks so
# tables spanning 3+ chunks still get the header (only overwritten by a NEW header).
```

**Flow:** HTML → markdownify (`strip=['script','style']`, no escapes, ATX headings; images kept only inside td/th/h1-h6 when extract_images=True) → preprocess kills SPA JSON blobs three ways (backtick-wrapped JSON regexes + json.loads validation of long `{`/`[`-prefixed lines — prefix check ALONE would eat markdown links) + collapse 4+ newlines → parse blocks → assemble with soft limit (single oversized block allowed) → build MarkdownChunk(content, chunk_index, total_chunks, char_offset_start/end, overlap_prefix, has_more) → `start_from_char` selects from the chunk whose `char_offset_end` first exceeds it.
**Invariant:** offsets must tile the original content exactly (test-pinned) — the +1-newline accounting and trailing-`\n` clamp are what make `start_from_char` pagination correct; table headers must persist until REPLACED, not reset per chunk; code fences and list items are never split mid-block.
**Probe:** `tests/ci/test_markdown_chunking.py` — offsets-cover-full-content (:31), trailing-newline clamp (:46), header-boundary splits (:64/:81/:96), fence/table/list atomicity (:114/:123/:135/:190), header carried across 3+ chunks (:169), start_from_char trio (:207/:221/:226); preprocessing pinned in `tests/ci/test_markdown_extractor.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "chunk_markdown_by_structure _parse_atomic_blocks MarkdownChunk overlap_prefix extract_clean_markdown", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-phase chunker (atomic grammar → header-preferred greedy → persistent-header overlap) and the JSON-blob preprocessing guards verbatim; adapt limits to your context budget; omit the HTML serializer coupling if you ingest markdown directly.
