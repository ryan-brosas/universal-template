<!-- capsule-v2 -->
# ApprovalRequiredToolset + ExternalToolset — approval gating and externally-produced results

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How does a porter gate tool calls behind human approval, and how does it represent tools whose results are produced outside the agent run (external/deferred)?

## ApprovalRequiredToolset gate + ExternalToolset placeholder
**Path/Symbol:** `pydantic_ai/toolsets/approval_required.py:ApprovalRequiredToolset` (15-32), `external.py:ExternalToolset` (15-46).
**Signature:** `ApprovalRequiredToolset(wrapped, approval_required_func=(ctx, tool_def, tool_args) -> True)`; `ExternalToolset(tool_defs, *, id=None)`.
**Data Shape:** `ApprovalRequiredToolset.call_tool` checks `ctx.tool_call_approved`; `ExternalToolset.get_tools` stamps `kind='external'`, `max_retries=0`, and a permissive `TOOL_SCHEMA_VALIDATOR` (`core_schema.any_schema()`).

### Decisive source
```python
# approval_required.py
async def call_tool(self, name, tool_args, ctx, tool):
    if not ctx.tool_call_approved and self.approval_required_func(ctx, tool.tool_def, tool_args):
        raise ApprovalRequired
    return await super().call_tool(name, tool_args, ctx, tool)

# external.py
TOOL_SCHEMA_VALIDATOR = SchemaValidator(schema=core_schema.any_schema())
async def get_tools(self, ctx):
    return {tool_def.name: ToolsetTool(
        toolset=self,
        tool_def=replace(tool_def, kind='external'),
        max_retries=0,
        args_validator=TOOL_SCHEMA_VALIDATOR) for tool_def in self.tool_defs}
async def call_tool(self, name, tool_args, ctx, tool):
    raise NotImplementedError('External tools cannot be called directly')
```

**Flow:** `ApprovalRequiredToolset` raises `ApprovalRequired` at `call_tool` when the call isn't already approved (`ctx.tool_call_approved` is False) and the predicate says approval is needed. The predicate receives `(ctx, tool_def, tool_args)`. `ExternalToolset` holds pre-built `tool_defs`, exposes them as `kind='external'` with `max_retries=0` and a permissive validator (anything validates), and its `call_tool` raises `NotImplementedError` — external tools cannot be invoked in-process; their results arrive via a deferred-tool-results mechanism.
**Invariant:** Approval is checked at call time (not listing time) and only when `ctx.tool_call_approved` is already False — an approved call bypasses the predicate. External tools are never directly callable (the `NotImplementedError` is the contract), and their args are unvalidated (`any_schema`) because validation happens on the external side.
**Probe:** `tests/test_toolsets.py` exercises approval wrappers; the `ApprovalRequired` exception path is covered by the deferred/approval test surface (see `tests/test_capabilities.py` deferral-legality tests).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "ApprovalRequiredToolset ExternalToolset kind external", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the call-time approval gate (predicate + `ctx.tool_call_approved` bypass) and the external-tool placeholder (kind stamp, zero retries, permissive validator, non-callable); adapt the `ApprovalRequired` exception to your host's approval mechanism; omit nothing — both are portable contracts. Coverage clean.
