<!-- capsule-v2 -->
# Chunk ladder — word → sentence → paragraph with exact-reconstruction ids

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How does a chunker guarantee that concatenated chunks reproduce the original text byte-for-byte while keeping deterministic chunk/paragraph identities?

## Three-level streaming chunker
**Path/Symbol:** `cognee/tasks/chunks/chunk_by_word.py:chunk_by_word` (:47-90), `chunk_by_sentence.py:chunk_by_sentence` (:32-102), `chunk_by_paragraph.py:chunk_by_paragraph` (:7-96); consumer `cognee/modules/chunking/text_chunker_with_overlap.py:TextChunkerWithOverlap.read` (:116-128).
**Signature:** `chunk_by_word(data) -> Iterator[(word, "word"|"sentence_end"|"paragraph_end")]`; `chunk_by_sentence(data, maximum_size=None) -> Iterator[(paragraph_id, sentence, size, cut_type)]`; `chunk_by_paragraph(data, max_chunk_size, batch_paragraphs=True) -> Iterator[dict{text, chunk_size, chunk_id, paragraph_ids, chunk_index, cut_type}]`.
**Data Shape:** `chunk_id = uuid5(NAMESPACE_OID, current_chunk)` — content-derived, so identical text ⇒ identical id (dedup for free).

### Decisive source
```python
# word level: whitespace attaches to the PRECEDING word; join("") == original
if re.match(SENTENCE_ENDINGS, character):        # [.;!?…。！？]
    # look ahead: trailing spaces join the punctuation token
    is_paragraph_end = next_i < len(data) and re.match(PARAGRAPH_ENDINGS, data[next_i])
    yield (current_chunk, "paragraph_end" if is_paragraph_end else "sentence_end")

# sentence level: paragraph_id rotates ONLY on paragraph_end
elif word_type in ["paragraph_end", "sentence_end"]:
    sentence += word; sentence_size += word_size
    paragraph_id = uuid4() if word_type == "paragraph_end" else paragraph_id
    yield (paragraph_id, sentence, sentence_size, word_type_state)

# overflow mid-sentence: cut_type records WHY the sentence was split
cut_type = "sentence_cut" if word_type_state == "word" else word_type_state
```

**Flow:** TextChunkerWithOverlap.read accumulates paragraph-batched chunk_data until `_accumulation_overflows` (`acc + size > max`) → emits from accumulation, then `_clear_accumulation` RETAINS tail entries fitting `chunk_overlap = max*ratio` as the next chunk's head → final tail flushed after the stream ends. Single oversized paragraph bypasses accumulation and keeps its own precomputed chunk_id. DocumentChunk id = `uuid5(NAMESPACE_OID, f"{document.id}-{chunk_index}")`.
**Invariant:** (1) Whitespace-before-word + punctuation-with-trailing-spaces tokens are what make `"".join(words)` an exact inverse — break this and embeddings/index offsets shift silently. (2) paragraph identity survives across sentence cuts inside one paragraph (only paragraph_end mints a new uuid4). (3) Overlap carry-over must keep ORDER (insert(0) walking reversed). (4) Token counting falls back to 1-per-word when the embedding engine has no tokenizer.
**Probe:** `cognee/tests/unit/processing/chunks/chunk_by_word_test.py`, `chunk_by_sentence_test.py::test_chunk_by_sentence_isomorphism`, `chunk_by_paragraph_test.py::run_chunking_test` (GROUND_TRUTH pins text/sizes/cut_types), `chunk_by_paragraph_2_test.py::test_chunk_by_paragraph_isomorphism`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "chunk_by_sentence paragraph uuid5 cut_type isomorphism", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the reconstruction-guaranteed token stream and content-derived uuid5 chunk ids; adapt sentence-ending charset and overlap ratio to your language/domain; omit LangchainChunker/JsonListChunker twins (same Chunker base).
