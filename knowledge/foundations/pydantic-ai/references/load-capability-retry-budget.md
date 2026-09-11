<!-- capsule-v2 -->
# Framework-injected meta-tool retry budget — what budget does `load_capability` run under and how do failed loads teach the model?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When the framework injects its own meta-tool (`load_capability`) alongside user tools, what retry budget does it get, and should a failed load crash the run or bounce back to the model?

## deferred-loader-meta-tool-contract
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/toolsets/_deferred_capability_loader.py:` `DeferredCapabilityLoaderToolset` (dataclass, `WrapperToolset` subclass, :34–108) — `get_tools` (:37–58), `call_tool` kind-dispatch (:64–68), `_load_capability` (:71–91).
**Signature:** `async def get_tools(ctx: RunContext[AgentDepsT]) -> dict[str, ToolsetTool[AgentDepsT]]`; loader tool built as `ToolsetTool(toolset=self, tool_def=…, max_retries=ctx.max_retries, args_validator=_load_capability_args_ta.validator)`.
**Data Shape:** reserved-name guard raises `UserError` if a user tool collides with `LOAD_CAPABILITY_TOOL_NAME`; the meta-tool's `ToolDefinition.tool_kind='capability-load'` stamp is what `call_tool` routes on (no name comparison); result dict seeds `{LOAD_CAPABILITY_TOOL_NAME: load_tool}` THEN `.update(all_tools)`.

### Decisive source
```python
load_tool = ToolsetTool(
    toolset=self,
    tool_def=load_tool_def,
    max_retries=ctx.max_retries,   # was hardcoded 1 before #6937
    args_validator=_load_capability_args_ta.validator,
)
...
if capability is None:
    raise ModelRetry(f'No capability found with id {capability_id!r}.')
if capability_id in ctx.available_capability_ids:
    raise ModelRetry(LOAD_CAPABILITY_ALREADY_AVAILABLE_MESSAGE_TEMPLATE.format(capability_id=capability_id))
```

**Flow:** get_tools wraps the inner toolset + injects the loader → model calls `load_capability({'id': …})` → unknown id ⇒ `ModelRetry` (model-visible, budget-consuming) → already-loaded ⇒ `ModelRetry` with the reuse-template (do-not-recall instruction) → success ⇒ `ToolReturn(return_value={'instructions': joined InstructionParts} , tools=sorted owned tool names or None)`.
**Invariant:** three rules:
1. A framework-injected tool inherits the AGENT'S tool retry budget (`ctx.max_retries`), never a private constant — hardcoding `1` meant one hallucinated deferred id exhausted the whole run while every real tool still had the agent budget (test pins `retries={'tools': 3}` → exactly 4 model calls, then `UnexpectedModelBehavior`).
2. Load failures are `ModelRetry`, never raised exceptions: the model can correct course; the run survives until the budget is truly gone.
3. Meta-tool routing rides `tool_kind`, not the tool name — user tools may not squat the reserved name (guarded at assembly time with a rename-prescribing `UserError`).
**Probe:** `tests/test_capabilities.py::test_load_capability_inherits_agent_tool_retries` (:4768–4795; asserts `calls == 4` under a 3-retry agent) — EXECUTED GREEN in repo `.venv` this pass; plus `grep -c "max_retries=ctx.max_retries" pydantic_ai_slim/pydantic_ai/toolsets/_deferred_capability_loader.py` → 1.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "load_capability inherits agent tool retries DeferredCapabilityLoaderToolset", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt budget-inheritance for framework meta-tools, ModelRetry-as-feedback for recoverable load failures, and the tool_kind routing + reserved-name guard; adapt message strings and the capability-id namespace to your host; omit the InstructionPart joining if your host has no dynamic-instruction channel (return the empty result dict instead).
