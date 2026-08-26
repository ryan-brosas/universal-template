<!-- capsule-v2 -->
# Turn-aware artifact compaction with schema-priority overflow ladder

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/artifact_compaction.py` (whole file, 170L).

## Path/Symbol
- `_compact_reference(msg) -> str` (:33) — THE shared compact-reference format
- `_swap_compact(messages, i, running_total) -> int` (:63) — O(1) token-delta update
- `shape_artifact_compaction(pin_first_n=1, trigger_ratio=0.5, keep_last_n_turns=1)` (:74)

## Signature
PRE_MODEL middleware; classifies artifact-bearing ToolMessages by `meta.turn_index < current_turn - keep_last_n_turns`.

## Data Shape
Compact reference = `[artifact:ID]`, `type:` (tool_name `__`→`.`), `tool:`, `args:` (200-char JSON cap), `tool_call_id:`, `summary:` (preview), optional `schema:` (full result_schema JSON), `original_tokens: N`, and a retrieval hint line naming `retrieve_artifact_content(artifact_id="…")`.

## Decisive source
```python
curr_with_schema.sort(key=lambda i: count_message_tokens(messages[i]), reverse=True)
for i in curr_with_schema:
    total = _swap_compact(messages, i, total)
    if total <= budget:
        break
# then curr_without_schema — largest-first within each tier
```

## Flow
Old-turn artifacts compact when context > `trigger_ratio × budget`. If still over ABSOLUTE budget, recent-turn results compact in priority order: (1) results WITH `result_schema` first (model can re-query via run_code later), (2) results WITHOUT (the model's only synthesis path) last. Largest-first within each tier; `_swap_compact` keeps a running token total instead of rescanning.

## Invariant
**The model that called a tool never saw the result inline** (results are appended after the model call), so `keep_last_n_turns=1` guarantees every fresh result is seen full at least once. Schema-bearing results are sacrificed before schema-less ones because their data remains machine-recoverable. The reference format is consumed by tool_result_clearing, deterministic_compact, synthesis_guard AND the sandbox bridge (`test_artifact_pipeline.py::TestSandboxBridgeResolution`) — changing it breaks four consumers.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_context_compaction.py`: `test_old_turn_compacted` (:122), `test_last_turn_kept_when_under_budget` (:140), `test_last_turn_compacted_when_over_budget` (:159), `test_current_turn_with_schema_compacted_first` (:195). Format pins: `test_artifact_pipeline.py::TestCompactReferenceFormat` :367–442.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["_compact_reference","artifact compaction","ToolMessageMeta"]'`

## Verdict
ADOPT. Two-phase design (registration at POST_TOOL_USE keeps current turn full; this shaper replaces older bodies turn-aware) + the schema-priority ladder is the reusable contract.
