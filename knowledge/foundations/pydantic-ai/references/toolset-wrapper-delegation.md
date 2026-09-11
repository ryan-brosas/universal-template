<!-- capsule-v2 -->
# Toolset Composition — how wrapper/combined toolsets delegate and merge

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When a porter builds a toolset that wraps or combines others, what delegation contract must every wrapper preserve so tools, instructions, lifecycle, and name-conflict errors behave identically to a plain toolset?

## AbstractToolset contract + WrapperToolset delegation
**Path/Symbol:** `pydantic_ai/toolsets/abstract.py:AbstractToolset` (76-281), `pydantic_ai/toolsets/wrapper.py:WrapperToolset` (14-74).
**Signature:** `AbstractToolset[AgentDepsT]` ABC with `id` (property), `label`, `tool_name_conflict_hint`, `for_run(ctx)`, `for_run_step(ctx)`, `__aenter__/__aexit__`, `get_instructions(ctx)`, `get_tools(ctx) -> dict[str, ToolsetTool]`, `call_tool(name, tool_args, ctx, tool)`, `apply(visitor)`, `visit_and_replace(visitor)`. `ToolsetTool` (43-73) = `{toolset, tool_def, max_retries, args_validator, args_validator_func}`.
**Data Shape:** `get_tools` returns a name→`ToolsetTool` dict (names are the wire contract — unique per agent). `call_tool` receives the SAME `tool` object that `get_tools` returned for that name (identity matters — wrappers pass it through). `for_run`/`for_run_step` default to returning `self` (shared across runs/steps) unless overridden.

### Decisive source
```python
# abstract.py — the leaf contract
async def get_tools(self, ctx) -> dict[str, ToolsetTool]: raise NotImplementedError()
async def call_tool(self, name, tool_args, ctx, tool): raise NotImplementedError()
def apply(self, visitor): visitor(self)          # leaf: visit self
def visit_and_replace(self, visitor): return visitor(self)
# wrapper.py — pure delegation; identity-preserving
async def get_tools(self, ctx): return await self.wrapped.get_tools(ctx)
async def call_tool(self, name, tool_args, ctx, tool):
    return await self.wrapped.call_tool(name, tool_args, ctx, tool)
async def get_instructions(self, ctx): return await self.wrapped.get_instructions(ctx)
def apply(self, visitor): self.wrapped.apply(visitor)
def visit_and_replace(self, visitor):
    return replace(self, wrapped=self.wrapped.visit_and_replace(visitor))
```

**Flow:** A wrapper holds `wrapped` and delegates every method. `for_run`/`for_run_step` return `self` when the inner `for_run*` returns the same instance (identity short-circuit), else `replace(self, wrapped=new_wrapped)`. `apply`/`visit_and_replace` recurse into the wrapped leaf so a visitor reaches the true leaf toolsets (those that implement their own listing/calling).
**Invariant:** A wrapper is transparent — it must not change tool identity (`tool` object passed to `call_tool` must be the same one `get_tools` returned), must delegate `get_instructions` (else wrapped instructions vanish from the system prompt), and must preserve `id`/`defer_loading` semantics. `visit_and_replace` rebuilds the hierarchy; `apply` is side-effect-only.
**Probe:** `tests/test_toolsets.py:test_wrapper_toolsets_delegate_instructions` (1660) and `test_wrapper_toolset_passes_through_instructions` (1928) — a `WrapperToolset` subclass must forward `get_instructions` to the wrapped toolset or the agent loses those instructions.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "AbstractToolset get_tools call_tool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ABC contract (id/label/get_tools/call_tool/for_run/for_run_step/apply/visit_and_replace) and the identity-preserving delegation pattern for any wrapper toolset; adapt `id`/`label` formatting to your host; omit nothing — this is the core reusable contract. Coverage clean on all cited paths (no_recorded_issue).
