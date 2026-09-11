<!-- capsule-v2 -->
# build_tool_return_part — what is the normalized shape of every settled function-tool result, and which malformed returns fail loudly?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How does a raw tool return value (or denial) become message history, optional user-visible content, and a tool-reveal request — and what inputs are rejected?

## The result normalizer
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_tool_execution.py:build_tool_return_part` (65–116); kind promotion at `_call_tool` (:704-713); denial branch (:76-86).
**Signature:** `build_tool_return_part(tool_result: Any, *, call: ToolCallPart, tool_kind: ToolPartKind | None) -> tuple[ToolReturnPart, str | Sequence[UserContent] | None, Sequence[str] | None]`.
**Data Shape:** Three outputs: (1) the history part (`content=return_value`, `metadata`, `tool_kind`), (2) optional user content (`ToolReturn.content` — separate from the model-visible return), (3) validated `ToolReturn.tools` name list. Plain values are wrapped into `ToolReturn(return_value=...)` before normalization.

### Decisive source
```python
# _tool_execution.py:88-107 — the two loud failures
if isinstance(tool_result, _messages.ToolReturn):
    tool_return = cast(_messages.ToolReturn[Any], tool_result)
elif isinstance(tool_result, list) and any(isinstance(item, _messages.ToolReturn) for item in ...):
    raise exceptions.UserError(
        f'The return value of tool {call.tool_name!r} contains invalid nested `ToolReturn` objects. '
        '`ToolReturn` should be used directly.')          # e.g. [ToolReturn(...)] is INVALID
...
tools = tool_return.tools
if tools is not None and (isinstance(tools, str) or not isinstance(tools, Sequence)
                          or any(not isinstance(name, str) for name in tools)):
    raise exceptions.UserError('`ToolReturn.tools` must be a list of tool names; pass a list of '
                               'strings instead of a bare string, non-sequence value, ...')

# :704-708 — typed identity survives multi-turn history
# If the called tool's `ToolDefinition.tool_kind` declares a registered typed subclass
# (e.g. `'tool-search'`), promote the return part to that subclass. This keeps the typed identity
# intact across multi-turn history: the next turn's discovery parser / cross-provider replay sees
# a typed `ToolSearchReturnPart` instead of a base part.
```

**Flow:** Settled result arrives (raw value / ToolReturn / ToolDenied from upstream dispatch) → denials short-circuit to `outcome='denied'` parts → everything else wraps to ToolReturn → validate `.tools` shape → build part → `narrow_type()` promotes base parts to registered typed subclasses by `tool_kind` so later turns can parse them type-safely.
**Invariant:** Nested `ToolReturn`s inside lists are rejected at the boundary (ambiguity about which value becomes content). The model-facing value and the human/user-facing content are DIFFERENT fields. Denial is representable in history without ever having run the tool.
**Probe:** snapshot-pinned throughout `tests/test_agent.py::TestMultipleToolCalls`; wire shapes pinned by `tests/test_tool_failed_wire.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "build_tool_return_part ToolReturn narrow_type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-output normalizer with loud failures on nested wrappers; adapt part classes to your message schema; omit typed-subclass promotion if you don't replay history across providers. Caveat: none — read at HEAD this session.
