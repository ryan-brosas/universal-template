<!-- capsule-v2 -->
# Streaming final_answer deltas — how do you surface an answer string token-by-token while it is still arriving inside a JSON tool-call argument?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you decode ONE named JSON string field from raw transport fragments — escapes split across chunk boundaries included — without buffering the whole tool call?

## StreamingJsonStringExtractor: a hand-rolled fragment-tolerant state machine
**Path/Symbol:** `backend/python/app/agent_loop_lib/core/json_stream.py:StreamingJsonStringExtractor` (L24–144); consumed at `agent/__init__.py:694–701` (per-index `_fa_extractors` map); direct test `tests/unit/agent_loop_lib/agent/test_json_stream.py` (30 tests).
**Signature:** `__init__(key: str)`; `feed(fragment: str) -> str` (returns newly decoded characters; no-op after done); `done -> bool`. States: scanning_key → scanning_colon → scanning_value_open → in_string ⇄ escape / unicode_escape → done.
**Data Shape:** Input = arbitrary string fragments of a JSON tool-call arguments document; output = decoded characters of the top-level `"key"` value only. Per-tool-call-index extractor instances live in a dict keyed by the provider's tool-call index.

### Decisive source
```python
if state == self._SCANNING_KEY:
    if ch == self._target[self._target_pos]:
        self._target_pos += 1
        ...
    else:
        # Mismatch — reset and try again from the start (greedy).
        # If the mismatching char itself starts the target, count it.
        self._target_pos = 1 if ch == self._target[0] else 0
...
elif state == self._ESCAPE:
    _SIMPLE = {"n": "\n", "r": "\r", "t": "\t", ...}
    if ch in _SIMPLE: ...
    elif ch == "u": self._state = self._UNICODE_ESCAPE
    else:
        # Unknown escape — emit as-is (lenient)
# unicode: accumulate 4 hex digits; invalid hex emits the RAW \uXXXX text

# Consumer side — one extractor per call index, None marks "not final_answer":
idx = event.index
if idx not in _fa_extractors:
    if final_answer_enabled() and event.name == FinalAnswerTool().name:
        _fa_extractors[idx] = StreamingJsonStringExtractor("answer_markdown")
    else:
        _fa_extractors[idx] = None   # not a final_answer call
decoded = extractor.feed(event.arguments_delta)   # → TEXT_MESSAGE_CONTENT delta
```

**Flow:** first arguments-delta for an index decides once whether the call is `final_answer` (name check + feature flag) → extractor feeds every subsequent delta, emitting decoded chars as TEXT_MESSAGE_CONTENT immediately (closing any open reasoning envelope first) → closing quote flips `done`; StreamCompleteEvent still carries the authoritative full response for history.
**Invariant:** (1) Presentation vs truth: streamed deltas NEVER enter history — exactly one StreamCompleteEvent remains the response of record (mirrors streaming-turn-loop). (2) The key scan must be greedy-resync (`"answer_markdown"` matched even when split mid-key AND when a partial match fails); KMP-ignorant reset counting the mismatch char is deliberate and sufficient here. (3) Every escape sequence (`\\`, `\"`, `\n..\f`, `/`, `\uXXXX`) must survive being SPLIT across fragments; invalid hex degrades to literal text, never raises. (4) Ollama sends args in ONE chunk — feed() called once must still work. (5) Non-final-answer tools get `None`, not an extractor — their deltas are intentionally dropped.
**Probe:** `tests/unit/agent_loop_lib/agent/test_json_stream.py` — :51–66 fragment splits (value/key/colon/one-char), :74–117 escape ladder incl. :94/:99/:104 escape-split-at-boundary, :119 wrong-key isolation, :146 key-prefix non-match, :155 invalid-unicode fallback, :161 ollama single-chunk.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "StreamingJsonStringExtractor feed done answer_markdown", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the state-machine extractor + per-index None-marker consumer pattern whenever answers ride inside tool-call args. Adapt target key name to host schema. Omit full JSON parsing (the point is decoding one string with O(1) state under fragmentation). No coverage caveat — this is the best-tested seam in the plane.
