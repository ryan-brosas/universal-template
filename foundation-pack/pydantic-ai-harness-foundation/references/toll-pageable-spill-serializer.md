<!-- capsule-v2 -->
# Pageable spill serializer: indented_json/json_lines presets keep read-back offsets on the line grid

## Source / Question
`pydantic_ai_harness/tool_output_limits/_payload.py:75–107` + `_capability.py:146–153, 288–308, 461–466` @ `main@f971198` (PR #638) — A spilled structured return stores as compact JSON: ONE long line, so the line-oriented `read_tool_result` pager returns everything on page 1 and nothing after. How do you make spills pageable without losing any tool output?

## Path / Symbol
`_payload.py` — `Serializer = Callable[[object], str]` (:75–76), `_LINE_SEPARATOR_ESCAPES = {0x85, 0x2028, 0x2029}` (:78–83), `indented_json` (:85–94), `json_lines` (:97–107), `_is_text_sequence` now also excludes `memoryview` (:131–134); `_capability.py` — new `serializer` field (:146–153), `_make_unit` try/warn/fallback (:288–306), Summarize nested run gains reserved limits (:458–461), `_ensure_text` guard (:464–466); presets re-exported from package `__init__`.

## Signature
```python
_LINE_SEPARATOR_ESCAPES = {0x85: '\\u0085', 0x2028: '\\u2028', 0x2029: '\\u2029'}
def indented_json(value): return to_json(value, indent=2).decode(...).translate(_LINE_SEPARATOR_ESCAPES)
def json_lines(value):
    if _is_text_sequence(value):            # Sequence minus str/bytes/bytearray/memoryview
        return '\n'.join(to_json(i).decode(...) for i in value).translate(_LINE_SEPARATOR_ESCAPES)
    return indented_json(value)             # dict/list-wrapped-in-dict falls back — return the list DIRECTLY
```

## Data Shape
The serialized TEXT is what gets measured, previewed, spilled, AND read back — so an indented layout can cross a band threshold compact JSON wouldn't (layout changes behavior deliberately, test-pinned). Strings/binary NEVER serialized; sub-threshold returns pass through as the original object untouched.

### Decisive source
Separator escaping rationale (:78–82): "`str.splitlines` treats these as line breaks, but JSON only requires escaping control characters below 0x20, so `to_json` emits them raw inside string values. Escaping them keeps read-back line slicing aligned with the lines the presets rendered" — U+0085/U+2028/U+2029 inside a VALUE would otherwise knock page offsets off the grid. Serializer failure path (:295–305): an after-hook exception would abort the run and LOSE the tool output, so a raising or non-text-returning serializer warns (`UserWarning`) and degrades to compact JSON — `_ensure_text` explicitly rejects bytes from `to_json(indent=2)` without `.decode()` (:464–466).

**Flow:** after-hook receives value → serializer renders (if set, non-str, non-binary) → measure → band action on rendered text → spill stores line-grid text → `read_tool_result(offset, limit)` pages per real record.
**Invariant:** broken serializer must never lose data or kill the run; json_lines line N == item N only for top-level sequences (a list inside a dict pages as one blob).

## Probe (direct test)
`tests/tool_output_limits/test_tool_output_limits.py` — preset shapes :151–170 (`json_lines([…]) == '{"a":1}\n{"b":2}'`, tuple-is-sequence, empty-list→'', separator escapes), `test_spill_serializer_json_lines_is_pageable` :466 (page1/page2 disjoint records), `test_serializer_layout_reaches_band_compact_would_not` :494, `test_serializer_error_warns_and_falls_back_to_compact` :503, non-text variant :515, strings-skipped :524, envelope-metadata preserved :484.

## Retrieve
```
search_graph --project pydantic-ai-harness --name-pattern 'indented_json json_lines _LINE_SEPARATOR_ESCAPES'
```

## Verdict
**Adopt** presets-with-escaping over raw custom serializers whenever spilled output is paged. **Adopt** warn-and-fallback over fail for output-shaping code. **Omit** json_lines if your tools return only scalars/strings.
