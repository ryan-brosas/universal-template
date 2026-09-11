<!-- capsule-v2 -->
# PrepareTools/PrepareOutputTools — callable prepare hooks with result validation on both tool planes

## Source / Question
`pydantic_ai_slim/pydantic_ai/capabilities/prepare_tools.py` (whole, 98L) @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Users want to filter/rewrite the tool list per step with a plain callable (sync or async) — but a buggy callable that ADDS or RENAMES tools would desynchronize what the model sees from what the engine registered. How do you expose the hook while keeping the tool surface closed? A porter will `await func(...)` unconditionally (breaks sync callables) and skip validation (model calls tools the agent can't execute).

## Path / Symbol
`prepare_tools.py` — `PrepareTools` (function-tool plane :13–44), `PrepareOutputTools` (output-tool plane :47–85; `ctx.retry`/`ctx.max_retries` reflect the OUTPUT retry budget `max_output_retries`, matching the output-hook lifecycle), shared `_call_prepare_func` (:88–98).

## Signature
```python
async def _call_prepare_func(prepare_func, ctx, tool_defs) -> list[ToolDefinition]:
    # `PreparedToolset.get_tools` validates that the result didn't add or rename tools
    # when these capabilities' hooks dispatch through it.
    result = prepare_func(ctx, tool_defs)          # call FIRST — works for sync AND async
    if inspect.isawaitable(result):
        result = await result
    return _utils.check_tools_prepare_func_result(result, prepare_func)   # no adds/renames
```

## Data Shape
Input/output: `list[ToolDefinition]` → same-shape list (filter/reorder/mutate-defs allowed). The capability pair is deliberately split by PLANE: function tools vs output tools get separate hooks because their retry budgets and lifecycle hooks differ; each returns `get_serialization_name() → None` (callable-carrying capabilities are excluded from spec serialization).

### Decisive source — dual-contract comment (:93–94)
```python
# `PreparedToolset.get_tools` validates that the result didn't add or rename tools
# when these capabilities' hooks dispatch through it.
```
The canonical usage examples in the docstrings are themselves the intended port shapes: hide-admin-tools filters by name prefix (:27–33); output-plane gate returns `[]` until `ctx.run_step > 0` ("only after first step", :62–65).

**Flow:** request build → capability chain invokes `prepare_tools(ctx, defs)` (or output twin) → callable may be sync or async (isawaitable branch) → validated result replaces that plane's tool list → model sees exactly the registered names.

**Invariant:** A user hook may REMOVE, REORDER, or MUTATE definitions but must never introduce an unknown name; support sync+async via call-then-await-if-awaitable; keep the two tool planes as separate hooks with plane-correct retry semantics.

**Probe:** `tests/test_capabilities.py::TestPrepareToolsCapability` (:8863 — filters via callable, rejects None-returning callable :8889, allows def mutation :8905) + `TestPrepareOutputToolsCapability` (:9030); `TestPrepareToolsHook` (:7174)/`TestPrepareOutputToolsHook` (:7289) pin the underlying hook planes.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'PrepareTools PrepareOutputTools check_tools_prepare_func_result'
```

## Verdict
**Adopt** the await-if-awaitable invocation + add/rename validation contract for any user-supplied tool-list hook. **Adapt** validation strictness (drop vs raise). **Omit** the dataclass-capability scaffolding if you already have a plugin API.
