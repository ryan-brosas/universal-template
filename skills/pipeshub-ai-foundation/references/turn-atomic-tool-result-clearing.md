<!-- capsule-v2 -->
# Turn-atomic tool-result clearing with metadata-only refs

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/tool_result_clearing.py` (whole file, 159L).

## Path/Symbol
- `_TOOL_REF_PREFIX = "tool: "`, `_LEGACY_CLEARED_PREFIX = "[cleared"` (:9–11)
- `_build_tool_ref(tool_name, tool_args, tool_call_id, content, is_error)` (:18)
- `shape_tool_result_clearing(keep_last_n_turns=3, trigger_ratio=0.5, protected_tool_names=None)` (:52)

## Signature
PRE_MODEL middleware; builds `call_id_to_turn/name/args` maps and a `turns: list[set[int]]` grouping message indices per logical turn.

## Data Shape
A "turn" = one AssistantMessage + ALL ToolMessages matching its tool_call ids. Five parallel calls in one assistant turn are ONE unit. Cleared non-artifact results become a metadata ref (`tool:`, `args:`, `tool_call_id:`, `error|summary:` preview, re-call hint); artifact-bearing ones get the shared `_compact_reference`.

## Decisive source
```python
turns = [t for t in turns if t]
turns.sort(key=lambda indices: min(indices))
if len(turns) <= keep_last_n_turns:
    await next_fn(); return
clearable: set[int] = set()
for turn_indices in turns[: len(turns) - keep_last_n_turns]:
    clearable.update(turn_indices)   # whole turn clears as a unit
```

## Flow
Fires above `budget.max_tokens * trigger_ratio`; protects the newest N turns; subtracts indices whose tool NAME is in `protected_tool_names` regardless of age; skips already-compacted content via prefix sniffing; orphans (no matching call) fall into their own singleton turn.

## Invariant
**Turn atomicity is deliberate**: clearing 2 of 5 parallel results from the same turn destroys coherent cross-referencing context, so eviction granularity is the TURN, never the individual ToolMessage. Idempotence relies on `_is_already_compact` prefix checks — a second pass must not double-replace.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_tool_result_clearing.py`: `TestTurnBasedGrouping::test_parallel_calls_are_one_turn` (:181), `test_parallel_calls_kept_as_unit` (:206), `TestArtifactAwareness::test_error_result_labeled_as_error` (:259), protection pins :98/:121.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["shape_tool_result_clearing","protected_tool_names","turn based clearing"]'`

## Verdict
ADOPT. Distinct from sliding-window eviction: it keeps message COUNT stable and replaces payloads with re-call hints, so the model retains what it did and can redo it cheaply.
