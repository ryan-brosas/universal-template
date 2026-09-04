<!-- capsule-v2 -->
# Two-layer tool-pairing invariant (boundary adjustment + final repair)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/_message_boundaries.py` (whole file, 152L).

## Path/Symbol
- `safe_tail_boundary(messages, raw_start, lower_bound) -> int` (:36)
- `repair_tool_pairing(messages) -> tuple[list[Message], int]` (:72)
- `shape_tool_pairing_repair()` — the "final PRE_MODEL middleware" wrapper (:129)

## Signature
`repair_tool_pairing` returns `(repaired_messages, repair_count)`; `shape_tool_pairing_repair()` is a zero-arg factory returning the async middleware.

## Data Shape
Layered defense: **prevention** (shapers call `safe_tail_boundary` when choosing head/middle/tail split points so the tail never starts with orphaned ToolMessages) + **repair** (`shape_tool_pairing_repair` runs LAST and drops whatever slipped through).

## Decisive source
```python
def safe_tail_boundary(messages, raw_start, lower_bound):
    if raw_start <= lower_bound or raw_start >= len(messages):
        return raw_start
    i = raw_start
    while i > lower_bound and messages[i].role == MessageRole.TOOL:
        i -= 1
    if i < raw_start and i >= lower_bound:
        msg = messages[i]
        if msg.role == MessageRole.ASSISTANT and getattr(msg, "tool_calls", None):
            return i
    return raw_start
```

## Flow
Repair pass 1 walks forward tracking `active_call_ids` from the most recent assistant-with-tool_calls; a ToolMessage whose id is not in that set is DROPPED (count incremented). Pass 2 strips orphaned tool_calls whose ToolMessages were dropped, via `msg.model_copy(update={"tool_calls": kept or None})`. Position-aware: **global ID presence is not sufficient** — a ToolMessage referencing a tool_call from an *earlier* assistant group is invalid once compaction removed intervening structure.

## Invariant
Providers 400 on unpaired tool messages (OpenAI: "messages with role 'tool' must follow 'tool_calls'"; Anthropic: tool_result needs tool_use). Repair deliberately LOSES information to save the LLM call; prevention moves boundaries instead. Repair must be registered after every shaper — production wires it at L9 in the platform factory (`factory.py :793`), NOT in ControlPlane.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_context_compaction.py::test_artifact_compaction_preserves_pairing` (:76) and `test_deterministic_compact_preserves_pairing` (:93) pin that shapers preserve `tool_call_id`/`tool_calls`; direct unit tests for `repair_tool_pairing` itself are absent — coverage caveat recorded.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["safe_tail_boundary","repair_tool_pairing","tool pairing"]'`

## Verdict
ADOPT. The porter's trap is treating tool-pairing as a per-shaper concern; pipeshub proves you need BOTH boundary-aware splitting AND one catch-all net at pipeline end.
