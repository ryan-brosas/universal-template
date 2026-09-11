<!-- capsule-v2 -->
# Content chunking — token estimation, density detection, JSON/text chunking with overlap

**Source:** graphiti MIT `<branch>@<commit>`; Codebase Memory `graphiti`. **Question:** how does an ingestion pipeline chunk large entity-dense content (JSON/text) into LLM-safe pieces with overlap, without chunking low-value prose?

## Connected graph-selected seam
**Path/Symbol:** `graphiti_core/utils/content_chunking.py` (826 lines): `estimate_tokens` (:39-51), `should_chunk` (:59-83), `_estimate_high_density` (:86), `chunk_json_content` (:215), `chunk_text_content` (:376), `_chunk_by_sentences` (:453), `_chunk_by_size` (:508).
**Signature:** `should_chunk(content, episode_type)` — chunks only if content is large (>= `CHUNK_MIN_TOKENS`) AND high entity density; `chunk_json_content`/`chunk_text_content` split with overlap.
**Data Shape:** token estimate via `len(text) // CHARS_PER_TOKEN` (~4 chars/token); JSON chunking splits arrays/objects with overlap elements; text chunking splits by sentences or size with overlap.

### Decisive source
```ts
def estimate_tokens(text): return len(text) // CHARS_PER_TOKEN  # ~4 chars/token, fast, provider-agnostic
def should_chunk(content, episode_type):
    tokens = estimate_tokens(content)
    if tokens < CHUNUNK_MIN_TOKENS: return False   # short content always fine
    return _estimate_high_density(content, episode_type, tokens)  # only dense content chunks
```

**Flow:** estimate tokens (character heuristic, fast, provider-agnostic) → `should_chunk` gates on size AND entity density (short or low-density prose never chunks, preserving context) → `chunk_json_content`/`chunk_text_content` split with overlap so no entity/context is lost at boundaries.
**Invariant:** chunking targets the specific failure case of large entity-dense inputs; short content and prose/narrative never chunk (context preserved); overlap prevents boundary loss.
**Probe:** `tests/` content-chunking tests (token estimate; should_chunk gates on density; JSON array/object chunking with overlap; text sentence/size chunking).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphiti", query: "should_chunk chunk_json_content chunk_text_content overlap density tokens", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the density-gated content chunking (token estimate, should_chunk on size+density, JSON/text split with overlap); adapt the token heuristic and chunk sizes to host.
