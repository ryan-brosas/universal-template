<!-- capsule-v2 -->
# Lazy toolset disclosure — how do you ship 3 tool schemas instead of 300 without locking agents out of the long tail?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** What does the model see this turn when the registry groups tools into toolsets, and what are the ceiling rules?

## Essentials + pinned upfront; fetch_tools grows visibility under a permission ceiling
**Path/Symbol:** `backend/python/app/agent_loop_lib/agent/tool_loop.py:initial_visible_tools` (168-186) and `tool_schemas_for_turn` (189-223); enforcement in `tools/builtin/lazy_toolsets.py` (`_grant_set` usage; fetch_tools/search_tools meta-tools); registry helpers `grouped_tool_names`/`tools_in_toolset` in `tools/registry.py`.
**Signature:** `def tool_schemas_for_turn(agent, spec, runtime) -> list[ToolSchema]`; `initial_visible_tools(spec, runtime) -> set[str]` = `(all_names − grouped) ∪ pinned_toolsets`, intersected with `spec.tool_names` when set.
**Data Shape:** visibility lives on RunScope (`agent.visible_tools: set[str] | None`), grown only by fetch_tools/search_tools/preloading — all of which enforce the same ceiling.

### Decisive source
```python
# tool_loop.py:202-221 — eager vs lazy when an explicit grant exists
if spec.tool_names:
    if spec.tool_disclosure == "lazy":
        # tool_names is a permission CEILING here, not an eager grant:
        # visibility starts at essentials/pinned ... and only grows via
        # fetch_tools/search_tools/preloading — all of which enforce the
        # same ceiling.
        return registry.schemas(sorted(agent.visible_tools & set(spec.tool_names)))
    # eager (default): the explicit tool grant is ALL named tools ...
    # Without this, a child agent spawned with a focused tool list would
    # be permanently locked out of grouped tools it was explicitly given,
    # since it lacks the list_toolsets/fetch_tools meta-tools needed to
    # discover and unlock them.
    return registry.schemas(spec.tool_names)
return registry.schemas(list(agent.visible_tools))
```

**Flow:** no toolsets ⇒ every schema every turn. With toolsets: first turn materializes `visible_tools = essentials+pinned (∩ ceiling)` → model calls fetch_tools to pull a group → visibility grows (ceiling-clamped) → next turn's schemas include them. Explicit grants default to EAGER so focused children always see exactly their granted list.
**Invariant:** A permission ceiling can only NARROW starting visibility, never widen beyond named tools; the intersection at :211 is a defensive no-op, not the sole enforcement point. Un-grouped tools are essentials by definition.
**Probe:** `tests/unit/agent_loop_lib/tools/test_lazy_toolsets.py` (fetch_tools growth + ceiling clamps); `tests/unit/agent_loop_lib/tools/test_toolset_builder_cache.py` (builder caching).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "initial_visible_tools tool_schemas_for_turn fetch_tools lazy toolsets ceiling", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt essentials-plus-pinned initial visibility with meta-tool growth under a strict ceiling, and eager-by-default for explicit child grants; adapt toolset grouping and meta-tool names to host; omit search_tools semantic ranking unless you have embeddings handy. Direct tests pin growth/clamp behavior via the lazy_toolsets suite.
