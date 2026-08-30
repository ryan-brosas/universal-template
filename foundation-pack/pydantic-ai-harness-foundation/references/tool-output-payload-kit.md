<!-- capsule-v2 -->
# Payload measurement kit: ANSI stripping, binary triage, annotated truncation, JSON sketches

## Source / Question
`pydantic_ai_harness/tool_output_limits/_payload.py` — Before any size-based reduction of a tool return, what is the payload, how big is it really (chars or tokens), and what do you show when you cut it? Porters str() everything — folding binary byte dumps into the corpus and truncating JSON into invalid fragments with no marker of what was lost.

## Path / Symbol
`tool_output_limits/_payload.py` — `TruncationStrategy = head|tail|head_tail` (:21–31), `_ANSI_ESCAPE_RE`/`strip_ansi` (:34–41), `is_binary`/`to_bytes` (:44–61), `to_text` (:64–72), `measure` (:75–80), `json_sketch` + TypeGuard guards (:83–113), `truncate_text` (:116–138).

## Signature
```python
def measure(text: str, *, over_tokens: bool, tokenizer: Callable[[str], int] | None) -> int:
    if not over_tokens:
        return len(text)
    message: ModelMessage = ModelRequest(parts=[SystemPromptPart(content=text)])
    return estimate_token_count([message], tokenizer)   # reuses the compaction heuristic

def truncate_text(text: str, max_chars: int, strategy: TruncationStrategy) -> str
```

## Data Shape
`to_bytes`: strings → UTF-8; bytes/memoryview verbatim; everything else → `pydantic_core.to_json` so spilled payloads stay valid and grep-able. `truncate_text` returns input unchanged when it fits; otherwise annotated cuts (`[truncated: showing first X of Y chars]`; head_tail splits 2/5 head + 3/5 tail with an omitted-count marker). `json_sketch`: `{'k': TypeName, ... , ... (N keys)}` for mappings (first 10 keys) / `[N items of ElemType]` for sequences; `''` for scalars.

### Decisive source
1. **Binary never stringified** (:44–46): `bytes|bytearray|memoryview` are triaged BEFORE any text path — "must never be stringify-truncated"; callers fall back instead (binary Truncate/Summarize defer to their `then`).
2. **Token unit alignment** (:75–80): token measuring wraps the text as a one-part message and calls `estimate_token_count`, deliberately reusing the compaction heuristic "so the two capabilities stay aligned" — two different estimators would make bands and compaction disagree about the same payload.
3. **ANSI stripped pre-measure** (:34–41): CSI + OSC + simple escapes regex; color codes "waste tokens and can confuse models."
4. **Annotations state the loss**: every truncation mode embeds a bracketed note of exactly what was removed (counts formatted with `,`), so a model knows the excerpt is partial and by how much.
5. **TypeGuard discipline** (:96–101): mapping/text-sequence narrowing via TypeGuard keeps strict typecheckers happy without `Any`.

## Flow / Invariant
Classify binary vs text → optional strip_ansi → measure in chosen unit → band-select upstream → truncate/sketch for display, to_bytes for spill. Invariant: the SAME measured value drives band selection that was rendered into the preview (measure once); JSON truncation is acknowledged lossy — prefer spill or summarize for structured values.

## Probe (direct test)
`tests/tool_output_limits/test_tool_output_limits.py::TestPayloadHelpers`: `test_strip_ansi` (:126), `test_is_binary` (:129), `test_to_bytes_variants` (:134), `test_measure_chars_and_tokens` (:144), `test_json_sketch_mapping_truncated` (:152), `test_truncate_head_tail` (:179), plus `TestTruncate::test_strip_ansi_applied` (:376).

## Retrieve
`search_graph --project pydantic-ai-harness --query 'strip_ansi json_sketch truncate_text measure to_bytes'`

## Verdict
**Adopt** the whole kit as the preamble to ANY size-gated content policy: classify → clean → measure → annotate loss. **Adopt** estimator-sharing between budgeting and reduction. **Adapt** thresholds and the head/tail ratio (here 40/60).
