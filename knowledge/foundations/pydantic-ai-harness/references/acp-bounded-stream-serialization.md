<!-- capsule-v2 -->
# ACP bounded stream serialization — why does a character-count cap fail to bound wire size, and what replaces it?

## Source / Question
`pydantic_ai_harness` (MIT) `main@76db3dec`; Codebase Memory project `pydantic-ai-harness`. **Question:** A newline-delimited-JSON stdio transport drops the connection when one notification overruns the client's read buffer — how do you split streamed text so EVERY chunk stays under budget regardless of Unicode content, and how do you shrink payloads that cannot be chunked?

## Path / Symbol
`pydantic_ai_harness/experimental/acp/_serialize.py` — whole module: `MAX_TEXT_UPDATE_BYTES` (:19), `MAX_RAW_FIELD_CHARS` (:23), `_escaped_len` (:26–37), `chunk_text` (:40–57), `jsonable` (:60–64), `bounded_jsonable` (:67–73).

**Signature:**
```python
def chunk_text(text: str, budget: int = MAX_TEXT_UPDATE_BYTES) -> Iterator[str]
def _escaped_len(char: str) -> int
def jsonable(value: object) -> object          # to_jsonable_python(value, fallback=str, bytes_mode='base64')
def bounded_jsonable(value: object) -> object
```

**Data Shape:** `MAX_TEXT_UPDATE_BYTES = 48 * 1024` (streamed text; envelope headroom below asyncio's default 64 KiB StreamReader limit). `MAX_RAW_FIELD_CHARS = 16 * 1024` (whole-payload tool input/output). Oversize marker shape: `{'truncated': True, 'original_length': <int serialized chars>, 'preview': <first MAX_RAW_FIELD_CHARS chars>}`.

### Decisive source
```python
# The SDK serializes outbound text with `json.dumps(..., ensure_ascii=True)`, so a non-ASCII code
# point expands *inside* the JSON string: a BMP char to `\uXXXX` (6 bytes) and an astral char to a
# surrogate pair `\uXXXX\uXXXX` (12 bytes). A character-count cap therefore can't bound the wire
# size -- 8K emoji serialize to ~96 KiB and drop the connection. We chunk by escaped byte length
# instead ...
    for char in text:
        char_size = _escaped_len(char)
        if chunk and size + char_size > budget:
            yield ''.join(chunk)
            chunk = []
            size = 0
```
Escape table (:26–37): short escapes → 2; control chars `<0x20` → 6 (`\u00XX`); ASCII → 1; BMP non-ASCII → 6; astral → 12. And the non-chunkable path (:67–73):
```python
    payload = jsonable(value)
    serialized = json.dumps(payload)
    if len(serialized) <= MAX_RAW_FIELD_CHARS:
        return payload
    return {'truncated': True, 'original_length': len(serialized), 'preview': serialized[:MAX_RAW_FIELD_CHARS]}
```

**Flow:** streamed model text → `_emit_text` splits via `chunk_text` → one `session/update` per chunk, each ≤ budget BY ESCAPED LENGTH → client reassembles. Tool input/output arrives whole per call → `jsonable` coerces first (`bytes_mode='base64'` keeps raw bytes from raising; `fallback=str` covers exotic types) → `bounded_jsonable` swaps oversize for the marker. Non-UTF-8 tool output becomes base64 (test: test_non_utf8_bytes_tool_output_is_base64_encoded); non-JSON objects fall back to str without crashing the stream.

**Invariant:** Wire-safety is measured in SERIALIZED bytes, never source characters or Python string length. Chunk boundaries may split anywhere (including mid-codepoint-neighborhoods) because the receiver concatenates text deltas. Anything that cannot be split must be truncated to a self-describing marker that still fits one notification.

**Probe:** `bash -c 'cd $REFERENCE_ROOT/pydantic-ai-harness && /tmp/harness-p6-venv/bin/python -m pytest "tests/experimental/acp/test_acp.py::TestChunkText" "tests/experimental/acp/test_acp.py::TestPermission::test_oversized_tool_output_is_truncated_in_the_update" "tests/experimental/acp/test_conformance.py::TestStreamedFrameBytes" -q'` — ascii byte-budget split, exact-fit single chunk, empty→nothing, non-ASCII stays in budget where a char cap would not; oversized output replaced by `"truncated": true` marker under cap+1024; wire-level frame-bytes conformance. (Executed this pass; see verification.md.)

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-ai-harness", query: "chunk_text escaped byte length budget MAX_TEXT_UPDATE_BYTES", limit: 5 });
```
Observed live: rank#1 `chunk_text` (_serialize.py :40–57) with direct tests as callers (`test_ascii_splits_by_byte_budget`, `test_non_ascii_stays_within_byte_budget_where_a_char_cap_would_not`, …); `bounded_jsonable` (:67–73) beside it.

## Verdict
**Adopt** escaped-byte-length accounting for any JSON-over-stdio/WebSocket stream where the reader buffer is fixed — port `_escaped_len` verbatim (it mirrors `ensure_ascii=True` exactly). **Adopt** the two-tier policy: chunkable streams split; atomic payloads truncate into `{truncated, original_length, preview}`. **Adopt** base64/fallback coercion BEFORE sizing so measurement sees the final form. **Adapt** budgets to your envelope overhead (48 KiB/16 KiB assume ~64 KiB readers). **Omit** pydantic-core specifics if your serializer escapes differently — then recompute the table. Caveat: none — unit + wire-conformance tests pin it at this pin.
