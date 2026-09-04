<!-- capsule-v2 -->
# Sliding window with atomic tool-group eviction

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/sliding_window.py` (whole file, 99L).

## Path/Symbol
- `shape_sliding_window(pin_first_n=1)` (:8)
- `_find_evictable(working, index_map, pinned) -> int | None` (:55)
- `_evict_group(working, index_map, evict_at)` (:77)

## Signature
PRE_MODEL middleware; loops `while total_tokens() > ctx.budget.effective_max_tokens and len(working) > 1`.

## Data Shape
`index_map: list[int]` tracks ORIGINAL indices through deletions so the pinned set (original indices of SYSTEM role / `msg.pinned` / first `pin_first_n`) stays valid while `working` shrinks. Eviction unit = assistant-with-tool_calls + immediately following ToolMessages whose `tool_call_id` matches its call ids.

## Decisive source
```python
def _find_evictable(working, index_map, pinned):
    first_tool_fallback: int | None = None
    for i in range(len(working)):
        if index_map[i] in pinned:
            continue
        if working[i].role == MessageRole.TOOL:
            if first_tool_fallback is None:
                first_tool_fallback = i   # only used if nothing else evictable
            continue                      # ToolMessages wait for their parent
        return i
    return first_tool_fallback
```

## Invariant
**Oldest-first eviction never splits a tool-call group**: ToolMessages are skipped as primary candidates and ride with their parent assistant message; the orphan fallback exists so pathological histories still shrink rather than loop forever. Runs on the OUTGOING call only — stored history is never mutated (`ctx.messages = working`).

## Probe
No direct unit test for this shaper (coverage caveat; grep over tests/ finds no `shape_sliding_window` import). Deterministic shape checks documented here instead: pinned-set arithmetic on original indices and group-extent deletion in `_evict_group` are the two behaviors a port must reproduce.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["shape_sliding_window","evict group","pinned messages"]'`

## Verdict
ADOPT. The `index_map` trick (pin by original index while deleting from a working copy) is the reusable primitive for any eviction policy that must respect stable "protected" markers.
