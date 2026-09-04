<!-- capsule-v2 -->
# Deterministic extractive compaction (LLM-free, identical-output)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/deterministic_compact.py` (whole file, 182L).

## Path/Symbol
- `_first_sentence(text, max_chars=300)` (:48)
- `_compact_assistant(msg)` (:57) — `[compacted]` prefix + tool_call names/ids
- `_compact_tool(msg, preview_chars, call_id_to_name, call_id_to_args)` (:75) — re-attaches tool NAME + ARGS to truncated results via a prebuilt call-id map
- `_compact_user(msg, max_chars=200)` (:103)
- `shape_deterministic_compact(trigger_ratio=0.85, keep_last_n_messages=6, pin_first_n=1, preview_chars=100)` (:116)

## Signature
PRE_MODEL middleware factory (Layer 6); replaces the LLM-backed `shape_auto_compact` summarizer with pure extraction.

## Data Shape
Per-class rules: System verbatim; human UserMessages verbatim; loop-compaction summaries verbatim (recognized via `_is_compaction_summary` import from loop_compaction); OTHER injected user messages → 200 chars; older assistants → first sentence + `[tool_calls: name(id), …]`; artifact tools → `_compact_reference`; plain tools → `tool_call_id`/name/args(200-char JSON)/preview block.

## Decisive source
```python
elif isinstance(msg, UserMessage):
    if _is_compaction_summary(msg):
        compacted_middle.append(msg)          # prior summaries survive intact
    elif getattr(msg, "injected", False):
        compacted_middle.append(_compact_user(msg))
    else:
        compacted_middle.append(msg)          # human-typed stays verbatim
```

## Invariant
**Identical input ⇒ identical output** (zero LLM calls, zero non-determinism). Human-typed messages are NEVER truncated — only programmatic injections are, because they grow unbounded. The `call_id_to_name/args` map is built over ALL messages (not just the middle) so truncated tool results keep their provenance.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_context_compaction.py::test_identical_input_identical_output` (:225) pins determinism; `test_deterministic_compact_preserves_pairing` (:93) pins pairing survival.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["shape_deterministic_compact","extractive compaction"]'`

## Verdict
ADOPT as the deterministic alternative to LLM summarization: same head/middle/tail split + `safe_tail_boundary`, but rule-based per message class.
