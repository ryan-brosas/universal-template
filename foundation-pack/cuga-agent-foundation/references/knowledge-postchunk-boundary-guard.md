<!-- capsule-v2 -->
# Post-chunk boundary guard — why does a char-length re-split corrupt token-bounded chunks, and what two safety nets replace it?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** After Docling/HybridChunker returns chunks, how does `_load_document` guarantee nothing exceeds the embedder's context without weakening the tokenizer-bounded guarantee — and how do docling chunker tokenizers stay zero-download?

## Exact-token strict guard (hf/tiktoken only) + 100k-char emergency net; chunker tokenizer = same tokenizer as embedder
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:5056-5198` (`_load_document` incl. both nets), `_build_docling_chunker` :4668-4770, `_tiktoken_docling_tokenizer_cls` :1216-1252, `_fastembed_docling_seq_limit` :1208-1213.
**Signature:** `def _load_document(self, file_path: Path) -> list[Document]`; `def _build_docling_chunker(self, chunk_size) -> HybridChunker | None`.
**Data Shape:** plain-text suffixes (.txt/.log/.json/.xml/.yaml/.toml/.ini/.cfg/.conf/.text) → read_text(errors="replace") + `_build_text_splitter`; everything else → DoclingLoader(ExportType.DOC_CHUNKS, converter, chunker?) with translated errors (`_translate_document_load_error`, unknown suffix → ValueError after Docling attempt).

### Decisive source
```python
# engine.py:5125-5147 (the unit-mismatch lesson) and :5158-5179 (the guard)
# The old version fired whenever any chunk's CHAR length exceeded
# ``chunk_size * 2`` ... That conflates two units:
#   - HybridChunker measures in TOKENS ...
#     bounded by min(chunk_size, model_max_seq_length)
#   - RecursiveCharacterTextSplitter measures in CHARS. Feeding it
#     ``chunk_size=800`` produced 800-char pieces, which for dense
#     content can be 600-800 XLM-RoBERTa tokens -- past e5-large's
#     512 ceiling. The embedder then silently truncated ...
if tok_info.kind in ("hf", "tiktoken"):
    over = sum(1 for d in docs
        if self._exact_chunk_tokens(d.page_content, tok_info) > tok_info.safe_max_tokens)
    ...
    docs = splitter.split_documents(docs)   # + one visible WARNING
_EMERGENCY_CHAR_THRESHOLD = 100_000         # ~25k tokens -- past any embedder
```
The chunker itself never downloads MiniLM: fastembed kind wraps its own ONNX tokenizer; hf kind wraps the embedder's AutoTokenizer (mutating transformers' fire-once warning flag instead of raising model_max_length, because HybridChunker MEASURES over-limit candidate windows before backing off); tiktoken kind is a local pydantic BaseTokenizer over cl100k_base (`count_tokens` with `disallowed_special=()`); HF-wrap failure falls back to tiktoken; total HybridChunker init failure returns None and the loader omits the chunker. cap = min(chunk_size, tok_info.safe_max_tokens) with a loud capping log.

**Flow:** dispatch by suffix → Docling path with cached converter + token-matched chunker → exact-token count per chunk for hf/tiktoken → any over safe_max ⇒ token-aware re-split + WARNING ("HybridChunker emitted an over-limit chunk — investigate if recurrent") → coarse 100k-char net for counter-less kinds (fastembed/approximate) → return. Counting failures are swallowed to `over=0` — the guard must never break ingest.
**Invariant:** Never compare a TOKEN budget against CHAR lengths (the old net split healthy chunks and weakened the token bound); the strict guard runs ONLY where an exact local counter exists and verifies against `safe_max_tokens` (already −16 margin), not raw model limit; every fallback level (HF wrap → tiktoken → default HybridChunker → None) degrades loudly but ingest continues.

**Probe:** `tests/unit/test_knowledge_resplit_unit_mismatch.py` — tokenizer dispatch :63/:92/:111/:131/:142/:155/:166, emergency threshold :189, resplit-is-token-aware :207, exact counters :228/:237, guard scoped+safe-max :248/:259, fire-once flag :279; chunker family also `test_knowledge_chunker_tokenizer.py`, `test_knowledge_chunker_hf_tokenizer.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_load_document _build_docling_chunker _exact_chunk_tokens safe_max_tokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: unit-discipline (tokens vs chars), exact-counter-scoped guard + coarse emergency net split, embedder-tokenizer reuse in the chunker (zero-download). Adapt thresholds to your embedder zoo. Omit the emergency net only if every path has an exact counter. Direct tests are extensive.
