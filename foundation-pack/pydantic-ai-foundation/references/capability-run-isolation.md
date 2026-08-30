<!-- capsule-v2 -->
# for_run / defer_loading — per-run capability state isolation and model-gated loading

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How do capabilities keep per-run mutable state safe across concurrent runs, and how can heavy tools stay hidden until the MODEL asks for them?

## AbstractCapability.for_run + defer_loading
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/capabilities/abstract.py:for_run` (:309-316), `id`/`defer_loading` fields (:200-228), `get_instructions`/`get_description` deferral notes (:328-352), `prepare_tools` deferred note (:454-459); loader in `capabilities/_deferred_capability_loader.py`, typed parts `capabilities/_deferred_capabilities.py`.
**Signature:** `async for_run(ctx: RunContext) -> AbstractCapability` (default: return self); `defer_loading: bool = False`; `id: str | None` (REQUIRED when deferred; else derived from class name).
**Data Shape:** Deferred capabilities surface ONE catalog tool (`load_capability`, `tool_kind='capability-load'` with typed call/return parts) whose args select by stable id; instructions/model-settings/toolset contributions resolve only after the load call.

### Decisive source
```python
# abstract.py:309-316 — the state-isolation seam, called once per run BEFORE re-extraction
async def for_run(self, ctx: RunContext[AgentDepsT]) -> AbstractCapability[AgentDepsT]:
    """Return the capability instance to use for this agent run.
    Called once per run, before get_*() re-extraction and before any hooks fire.
    Override to return a fresh instance for per-run state isolation.
    Default: return `self` (shared across runs)."""
    return self

# abstract.py:216-227 — the model-gated loading contract
# defer_loading: If True, model-facing tools and instructions are hidden until the model explicitly
# loads the capability via the load_capability tool.
# Model settings and lifecycle hooks are registered during run setup, but only apply or fire once
# the capability is loaded. Requires a stable `id` so message history can identify the capability.

# abstract.py:454-459 — why prepare_tools is a no-op pre-load
# On a deferred capability this runs only once the capability is loaded ... an unloaded capability's
# tools are neither advertised to the model nor callable, so no filtering here could change what
# the model can reach.
```

**Flow:** Run setup → each capability's `for_run(ctx)` may swap in a fresh instance (its `get_*` contributions re-extracted from THAT instance; wrap hooks still chain through the original list position) → if `defer_loading`: register settings/hooks up front but contribute NO model-facing tools/instructions until the model calls `load_capability(id=…)` → loader promotes typed `LoadCapabilityCallPart/ReturnPart` parts into history so replay shows when each capability became active.
**Invariant:** Identity-based ordering refs (`CapabilityRef` instances) stop matching after `for_run` returns a copy — the docstring warns to use TYPE refs for stateful targets. Per-run ContextVars set in hooks don't propagate bidirectionally across async boundaries: durable per-run state belongs ON the `for_run` copy's attributes.
**Probe:** `tests/test_capabilities.py::test_deferred_hooks_do_not_fire_until_capability_is_loaded` (:2900), `::test_combined_capability_skips_unloaded_deferred_forward_hooks` (:5260), `tests/test_messages.py::test_narrow_message_parts_promotes_valid_claims_and_leaves_plain_parts` (:2317 — load-capability parts in history).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "for_run defer_loading load_capability _deferred_capability_loader", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the for_run copy seam for concurrency-safe capability state and the single-catalog-tool lazy-loading pattern with history-typed parts; adapt naming/id resolution; omit defer_loading if your tool count never threatens context size. Caveat: source read at HEAD this session; loader internals partially verified via tests + typed-part registry rather than full-file read of `_deferred_capability_loader.py`.
