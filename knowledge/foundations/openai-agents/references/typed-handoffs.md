<!-- capsule-v2 -->
# Typed handoffs — delegation with session/model history split and redaction-aware errors

**Source:** OpenAI Agents Python MIT `main@cb8a2e7e7dd83a427cff9076e58356d00c4f90b2`; Codebase Memory `openai-agents-python`. **Question:** How does an agent hand off to another with typed input, without corrupting durable history, and without leaking secrets through errors?

## Typed handoff delegation
**Path/Symbol:** `src/agents/handoffs/__init__.py:Handoff` / `handoff()` / `HandoffInputData` / `_invoke_handoff_with_redaction` (1-388).
**Signature:** `handoff(agent, *, tool_name_override=None, tool_description_override=None, on_handoff=None, input_type=None, input_filter=None, nest_handoff_history=None, is_enabled=True)`.
**Data Shape:** `Handoff` wraps a target `Agent` with an optional TYPED `input_type` (validated via `TypeAdapter` → strict JSON schema via `ensure_strict_json_schema`), exposed to the calling model as a TOOL (`tool_name` defaults to `transfer_to_<agent.name>`). `HandoffInputData{input_history, pre_handoff_items, new_items, run_context=None, input_items=None}`.

### Decisive source
```python
class HandoffInputData:
    input_history: str | tuple[TResponseInputItem, ...]
    pre_handoff_items: tuple[RunItem, ...]
    new_items: tuple[RunItem, ...]          # full, for session history
    input_items: tuple[RunItem, ...] | None = None  # filtered, for the NEXT agent's INPUT

# input_items docstring (:94-99): "allows filtering duplicates from agent input while
# preserving all items in new_items for session history."
```

**Flow:** `handoff()` builds the tool schema, always strict-mode (`ensure_strict_json_schema`). On invoke, `_invoke_handoff_with_redaction` wraps the call: if a `ModelBehaviorError` is data-redacted, it DETACHES the traceback, nulls ctx/input, sets `input_json="<redacted>"`, and re-raises — secrets that tripped inside a handoff never leak through error objects. The session/model split: `input_items` (filtered) feeds the next agent's INPUT while `new_items` (full) stays in SESSION HISTORY — an `input_filter` can slim what the next agent sees without corrupting durable history. Filter results are validated before trust (non-callable → UserError; non-`HandoffInputData` return → UserError). Server-managed conversations (conversation_id/previous_response_id/auto_previous_response_id) do NOT support input filters (raise UserError verbatim); nesting silently downgrades with a warning.
**Invariant:** Display vs persistence are separate — filtering the next agent's input must never mutate the durable history.
**Probe:** `tests/test_handoffs.py`, `tests/test_handoff_history_duplication.py` (input_items filtering keeps new_items intact), `tests/test_handoff_prompt.py`, `tests/test_handoff_tool.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", query: "HandoffInputData input_items handoff", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt typed-handoff tool schema, the session/model input split, and redaction-aware error propagation; adapt the default tool-name transform; omit server-managed-conversation specifics. Direct tests pin the duplication and redaction behavior.
