<!-- capsule-v2 -->
# ExternalToolset & ApprovalRequiredToolset — how do toolsets declare deferral kinds and gate calls on approval?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** What is the minimal toolset surface for (a) exposing tools whose results come from outside the run, and (b) wrapping any toolset so some calls require approval first?

## Two tiny toolsets, two mechanisms
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/toolsets/external.py:ExternalToolset` (15–46); `toolsets/approval_required.py:ApprovalRequiredToolset` (15–32) over `toolsets/wrapper.py:WrapperToolset`.
**Signature:** `ExternalToolset(tool_defs: list[ToolDefinition], *, id=None) :: AbstractToolset`; `ApprovalRequiredToolset(approval_required_func: Callable[[RunContext, ToolDefinition, dict[str, Any]], bool] = lambda ctx, tool_def, tool_args: True)` extending `WrapperToolset`.
**Data Shape:** Toolsets expose `get_tools(ctx) -> dict[str, ToolsetTool]` where `ToolsetTool{toolset, tool_def, max_retries, args_validator}`; execution enters via `call_tool(name, args, ctx, tool)`.

### Decisive source
```python
# external.py:32-46 — kind is stamped at DEFINITION level; the body is unreachable
async def get_tools(self, ctx):
    return {
        tool_def.name: ToolsetTool(
            toolset=self,
            tool_def=replace(tool_def, kind='external'),
            max_retries=0,
            args_validator=TOOL_SCHEMA_VALIDATOR,   # shared module-level any-schema validator
        )
        for tool_def in self.tool_defs
    }

async def call_tool(self, name, tool_args, ctx, tool):
    raise NotImplementedError('External tools cannot be called directly')

# approval_required.py:26-32 — the gate is a context flag, not wrapper removal
async def call_tool(self, name, tool_args, ctx, tool):
    if not ctx.tool_call_approved and self.approval_required_func(ctx, tool.tool_def, tool_args):
        raise ApprovalRequired
    return await super().call_tool(name, tool_args, ctx, tool)
```

**Flow:** ExternalToolset stamps `kind='external'` during `get_tools`, so classification happens upstream in the executor — `call_tool` raising `NotImplementedError` is a backstop, not the mechanism. ApprovalRequiredToolset wraps an inner toolset; each call consults a predicate; a miss raises `ApprovalRequired` which the executor collects into the batch; when resolution approves with the SAME call id, re-validation builds the context with `approved=True`, setting `ctx.tool_call_approved` so the second pass slips through the predicate.
**Invariant:** The approval gate keys off `ctx.tool_call_approved` rather than unwrapping the wrapper — one wrapper stays in the chain forever, and denial/approval can't desynchronize from the inner toolset identity. External tools carry `max_retries=0` (there is no in-run retry loop for a result produced elsewhere). The predicate receives validated args only at call time; deferral-before-valid-args is forbidden by `ToolManager._validate_hook_deferral_error`.
**Probe:** `tests/test_toolsets.py` pins toolset composition incl. external; approval flow pinned by the `tests/test_agent.py` approval suite.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ExternalToolset ApprovalRequiredToolset WrapperToolset call_tool get_tools", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt definition-level kind stamping + context-flag approval gates; adapt `ToolDefinition` to your host's tool metadata record; omit the shared any-schema validator if your validation layer differs. Caveat: none — both files read in full this session.
