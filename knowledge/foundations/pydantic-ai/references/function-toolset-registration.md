<!-- capsule-v2 -->
# FunctionToolset registration + call — option inheritance, loud conflicts, timeout→ModelRetry

**Source:** pydantic-ai (MIT) `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** When tools are registered on a function toolset and later called, how do toolset-level defaults merge with per-tool overrides, when is a name conflict an error, and what does a tool timeout produce?

## FunctionToolset.add_tool / add_function inheritance + call_tool timeout
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/toolsets/function.py:FunctionToolset.add_function` (541-578), `add_tool` (580-592), `get_instructions` (594-606), `call_tool` (678-692).
**Signature:** `add_function(func, takes_ctx=None, name=None, retries=None, ... ) -> Tool`; `async call_tool(name, tool_args, ctx, tool) -> Any`.
**Data Shape:** `None` = "inherit from toolset"; `metadata: dict | None` merged as `{toolset_meta} | {tool_meta}` (tool wins per key).

### Decisive source
```python
# add_tool: registration-time rules
if tool.name in self.tools:
    raise UserError(f'Tool name conflicts with existing tool: {tool.name!r}')
if tool.max_retries is None and self.max_retries is not None:
    tool.max_retries = self.max_retries          # bake the default in at registration
if self.metadata is not None:
    tool.metadata = self.metadata | (tool.metadata or {})   # toolset base, tool overrides

# get_instructions: strings vs runner functions; dynamic flag differs
if isinstance(func, str):
    if func.strip(): parts.append(InstructionPart(content=func, dynamic=False))
else:
    result = await func.run(ctx)
    if result and result.strip(): parts.append(InstructionPart(content=result, dynamic=True))

# call_tool: timeout converts to a RETRY PROMPT for the model
timeout = tool.timeout if tool.timeout is not None else self.timeout  # per-tool wins
if timeout is not None:
    try:
        with anyio.fail_after(timeout):
            return await tool.call_func(tool_args, ctx)
    except TimeoutError:
        raise ModelRetry(f'Timed out after {timeout} seconds.') from None
```

**Flow:** register → inherit unset options from the toolset (retries baked immediately; metadata merged toolset-first) → duplicate names raise at REGISTRATION time → at call time resolve timeout per-tool-then-toolset → on expiry convert `TimeoutError` into `ModelRetry` so the model sees a corrective prompt rather than a crashed step.
**Invariant:** Conflicts fail loudly at registration, never silently overwrite. Per-tool timeout beats toolset timeout; absence of both means no timeout. A timed-out tool is a retryable condition (`ModelRetry`), not a terminal error. Toolset instructions emit `dynamic=False` for literals and `dynamic=True` for computed values.
**Probe:** `tests/test_toolsets.py` FunctionToolset suites (registration/conflict behavior around 150+); timeout→ModelRetry exercised via toolset tests with `fail_after`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "FunctionToolset add_tool metadata max_retries ModelRetry TimeoutError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt registration-time conflict detection, the None-means-inherit convention, and timeout-as-retry-prompt; adapt the option set to your host's tool config; omit anyio specifics if your runtime has another cancellation primitive. Coverage clean.
