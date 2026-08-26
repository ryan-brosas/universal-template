<!-- capsule-v2 -->
# Token chunking — tokenizer-driven sliding window with overlap

**Source:** graphrag MIT `<branch>@<commit>`; Codebase Memory `graphrag`. **Question:** how does an indexing pipeline split documents into token-accurate chunks with overlap, behind a pluggable chunker ABC?

## Connected graph-selected seam
**Path/Symbol:** `graphrag-chunking` package: `Chunker` (ABC, `chunker.py:13`) — `chunk(text, transform?) -> list[TextChunk]`; `TokenChunker` (`token_chunker.py:14`) + `split_text_on_tokens` (:45-69); `SentenceChunker` (`sentence_chunker.py:17`); `chunker_factory.py`; `TextChunk` model; `create_chunk_results`.
**Signature:** `split_text_on_tokens(text, chunk_size, chunk_overlap, encode, decode)` — encode once, slice the token array with a sliding window stepping `chunk_size - chunk_overlap`, decode per window.
**Data Shape:** `TextChunk {text_chunk, n_tokens(?), source_doc?}`; optional `transform: Callable[[str], str]` applied at result creation.

### Decisive source
```ts
def split_text_on_tokens(text, chunk_size, chunk_overlap, encode, decode):
    input_tokens = encode(text)                      # one encode pass
    start_idx = 0
    cur_idx = min(start_idx + chunk_size, len(input_tokens))
    while start_idx < len(input_tokens):
        result.append(decode(input_tokens[start_idx:cur_idx]))
        if cur_idx == len(input_tokens): break
        start_idx += chunk_size - chunk_overlap      # step = size minus overlap
        cur_idx = min(start_idx + chunk_size, len(input_tokens))
```

**Flow:** Chunker ABC defines `chunk(text, transform)` → TokenChunker encodes the whole doc once, windows the token ids (never re-tokenizes boundaries), decodes each window → SentenceChunker splits on sentence boundaries instead → factory selects by config → `create_chunk_results` wraps strings into `TextChunk`s applying the optional transform.
**Invariant:** chunking happens in token space (accurate LLM sizing), not character space; overlap < size guarantees forward progress; a single encode pass avoids repeated tokenization cost.
**Probe:** `tests/` chunking tests (token counts per chunk ≤ size; consecutive chunks share overlap tokens; final partial chunk emitted; transform applied).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "TokenChunker split_text_on_tokens chunk_overlap TextChunk Chunker", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt token-space sliding-window chunking (single encode, size−overlap step) behind a two-strategy ABC (token/sentence); adapt sizes and tokenizer to host.
