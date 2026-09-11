<!-- capsule-v2 -->
# Speaker-message chunking — never split mid-message, overlap by whole messages

**Source:** graphiti MIT `main@993e081a`; Codebase Memory `mnt-hdd-utopia-inspo-memory-graphiti`. **Question:** how do you chunk conversation transcripts so chunk boundaries never cut a message and overlap carries WHOLE boundary messages?

## Speaker-message chunking
**Path/Symbol:** `graphiti_core/utils/content_chunking.py`: `chunk_message_content` (:549-593), `_chunk_speaker_messages` (:607-651), `_get_overlap_messages` (:654-669), `_chunk_by_lines` fallback (:672-706); env knobs in `graphiti_core/helpers.py:45-55` (`CHUNK_TOKEN_SIZE` 3000 / `CHUNK_OVERLAP_TOKENS` 200).
**Signature:** `chunk_message_content(content, chunk_size_tokens=None, overlap_tokens=None) -> list[str]` — dispatch order: JSON array → speaker pattern → line-based.
**Data Shape:** sizes converted token→chars via `CHARS_PER_TOKEN = 4` (`_tokens_to_chars`, :54-56); a single message larger than the whole budget becomes its OWN chunk (never truncated).

### Decisive source
```python
# Dispatch ladder: JSON array of message objects first, then "Speaker: msg" prose,
# then plain lines:
try:
    data = json.loads(content)
    if isinstance(data, list):
        return _chunk_message_array(data, chunk_size_chars, overlap_chars)
except json.JSONDecodeError:
    pass
speaker_pattern = r'^([A-Za-z_][A-Za-z0-9_\s]*):(.+?)(?=^[A-Za-z_][A-Za-z0-9_\s]*:|$)'
if re.search(speaker_pattern, content, re.MULTILINE | re.DOTALL):
    return _chunk_speaker_messages(content, chunk_size_chars, overlap_chars)
return _chunk_by_lines(content, chunk_size_chars, overlap_chars)

# Split BEFORE each line-starting "Speaker:" via zero-width lookahead:
pattern = r'(?=^[A-Za-z_][A-Za-z0-9_\s]*:)'
messages = re.split(pattern, content, flags=re.MULTILINE)

# Oversize single message = its own chunk; flush current buffer first:
if msg_size > chunk_size_chars:
    if current_messages:
        chunks.append('\n'.join(current_messages))
        ...
    chunks.append(message)
    continue

# Boundary accounting counts the JOIN separator (+1) per accumulated message:
if current_messages and current_size + msg_size + 1 > chunk_size_chars:
    ...overlap_messages = _get_overlap_messages(current_messages, overlap_chars)
    current_size = sum(len(m) for m in current_messages) + len(current_messages) - 1
```

**Flow:** oversize check on raw chars → format detection → split into atomic messages → greedy pack with `len(msg)+1` accounting → on overflow flush chunk and RESEED the next buffer with the tail messages that fit inside `overlap_chars` (`_get_overlap_messages` walks `reversed(messages)` inserting at front until one more would exceed the budget — at least the just-flushed last message usually carries over) → final flush; empty result ⇒ `[content]`.
**Invariant:** (1) message atomicity is absolute — an oversized message is emitted alone, never split mid-text; (2) overlap is computed from the PREVIOUS chunk's messages only, in original order, whole-message granularity (contrast `_chunk_by_lines`, which re-splits its overlap text on '\n'); (3) the speaker regex requires identifier-start (`[A-Za-z_]`) so digit-led lines never look like speakers; (4) all size math is CHARS derived from tokens at 4 chars/token — do not mix token and char units when tuning env knobs.
**Probe:** `.venv/bin/python -m pytest tests/utils/test_content_chunking.py::TestChunkMessageContent -q` (speaker format preserved; JSON arrays chunked; small content untouched). Anchored at repo root. Battery: `grep -cF '(?=^' graphiti_core/utils/content_chunking.py` → 2; `grep -c 'current_size + msg_size + 1 > chunk_size_chars' graphiti_core/utils/content_chunking.py` → 1; `grep -c 'CHUNK_DENSITY_THRESHOLD \* 500' graphiti_core/utils/content_chunking.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-memory-graphiti", query: "chunk_message_content _chunk_speaker_messages _get_overlap_messages", limit: 5, fields: ["signature", "name", "file"] });
// rank-1..3 resolve line-exact to :607-669/:549-593 + TestChunkMessageContent
```

## Verdict
Adopt atomic-message packing with whole-message overlap and the three-way format dispatch; adapt regexes to your transcript dialects (e.g. timestamps, brackets); omit JSON-array branch if your episodes are never serialized transcripts. Direct tests run in default CI.
