<!-- capsule-v2 -->
# remove_all_tools handoff input filter — how does a handoff strip tool noise from every history lane without breaking chained filters?

**Source:** OpenAI Agents Python MIT `main@fe45b415ee05`; Codebase Memory project `openai-agents-python` (MCP absent this pass — direct source+test reading fallback per AGENTS.md). **Question:** When an agent hands off to a specialist, how does the input filter remove tool-call artifacts from the conversation the new agent sees — across raw dict history AND typed RunItem lanes — while composing safely with history nesting and session-history preservation?

## Handoff input filter
**Path/Symbol:** `src/agents/extensions/handoff_filters.py:` `remove_all_tools` (:33–56), `_remove_tools_from_items` (:59–78), `_remove_tool_types_from_input` (:80–118).
**Signature:** `def remove_all_tools(handoff_input_data: HandoffInputData) -> HandoffInputData`.
**Data Shape:** `HandoffInputData` has four lanes: `input_history: str | tuple[TResponseInputItem, ...]`, `pre_handoff_items: tuple[RunItem, ...] | None`, `new_items: tuple[RunItem, ...]`, `input_items: tuple[RunItem, ...] | None`; filtering returns a `clone()` with all four lanes replaced.

### Decisive source
```python
# Preserve and filter input_items so chained filters (e.g. after
# nest_handoff_history) don't drop or re-introduce tool items.
existing_input_items = handoff_input_data.input_items
filtered_input_items = (
    _remove_tools_from_items(existing_input_items) if existing_input_items is not None else None
)
return handoff_input_data.clone(
    input_history=filtered_history,
    pre_handoff_items=filtered_pre_handoff_items,
    new_items=filtered_new_items,
    input_items=filtered_input_items,
)
```
and the two vocabularies it must filter:
```python
# dict-shaped model input: blocklist by type string (26 entries)
tool_types = ["function_call", "function_call_output", "computer_call",
    "computer_call_output", "file_search_call", "tool_search_call", "tool_search_output",
    "web_search_call", "mcp_call", "mcp_list_tools", "mcp_approval_request",
    "mcp_approval_response", "reasoning", "code_interpreter_call", "image_generation_call",
    "local_shell_call", "local_shell_call_output", "shell_call", "shell_call_output",
    "apply_patch_call", "apply_patch_call_output", "custom_tool_call",
    "custom_tool_call_output", "hosted_tool_call", "program", "program_output"]
# typed RunItem lanes: isinstance over 11 classes
if (isinstance(item, HandoffCallItem) or isinstance(item, HandoffOutputItem)
    or isinstance(item, ToolSearchCallItem) or isinstance(item, ToolSearchOutputItem)
    or isinstance(item, ToolCallItem) or isinstance(item, ToolCallOutputItem)
    or isinstance(item, ReasoningItem) or isinstance(item, MCPListToolsItem)
    or isinstance(item, MCPApprovalRequestItem) or isinstance(item, MCPApprovalResponseItem)
    or isinstance(item, ToolApprovalItem)):
    continue
```

**Flow:** `input_history` is filtered only when it is a tuple of dict-shaped input items (a plain string passes through untouched); `pre_handoff_items`, `new_items`, and `input_items` are filtered by the RunItem isinstance set; the result is a `HandoffInputData.clone(...)` — the original is never mutated. The `input_items` lane exists so a chained mapper can filter what the MODEL receives while `new_items` stays intact for session history (`handoffs/__init__.py` :94, :166–167); `remove_all_tools` filters it too, so a filter placed AFTER `nest_handoff_history` cannot re-introduce tool items that nesting moved into `input_items` — the canonical chain is `remove_all_tools(nest_handoff_history(data))`.

**Invariant:** (1) All four lanes are filtered, not just the visible history — a filter that skips `input_items` silently leaks tool items into model input when composed after nesting. (2) String history is never touched (nothing to filter, no crash on `.get`). (3) The filter is pure: it clones, never mutates, the input data. (4) The type blocklist and the isinstance set must cover the same tool families (shell/apply_patch/local_shell/custom/hosted calls and outputs, MCP list/approvals, reasoning, tool search) or one vocabulary or the other leaks.

**Probe:** `tests/test_extension_filters.py` — `test_empty_data` (:182, no-op on empty), `test_str_historyonly` (:188, string history untouched), `test_str_history_and_list` (:196), `test_list_history_and_list` (:205); `tests/test_handoff_history_duplication.py` :786 (`remove_all_tools(nest_handoff_history(data))` chained composition); `tests/test_stream_events.py` :313/:702 (end-to-end handoff with the filter attached).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "openai-agents-python", query: "handoff input filter remove tool items clone input_items nest history", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-lane clone-and-filter shape with the dual vocabulary (type-string blocklist for dict history, isinstance set for RunItem lanes) and the filter-`input_items`-too rule for chain safety. Adapt the blocklist/isinstance sets to your own item taxonomy — the invariant is coverage parity between the two vocabularies, not the specific 26/11 lists. Omit the string-history passthrough only if your history is always structured. Coverage caveat: MCP absent this pass; Retrieve block is the canonical shape, not an executed call; all citations line-verified by grep against HEAD fe45b415ee05.
