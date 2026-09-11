<!-- capsule-v2 -->
# Tool-reveal guardrails — how can a tool dynamically reveal other tools without letting parallel calls race or bypass capability loading?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** When a tool's `ToolReturn.tools` names follow-up tools, what validation and dedup rules keep the emitted history deterministic?

## Reveal rejection + assembly-time pruning
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_tool_execution.py:_reject_unloaded_capability_reveals` (170–201), `_prune_duplicate_tool_reveals` (204–229), delta emission in `_call_tool` (:715-733) and the exhaustive append loop (:1233-1260).
**Signature:** `_reject_unloaded_capability_reveals(tools: Sequence[str], tool_manager, *, activating_capability_id: str | None = None) -> None`; `_prune_duplicate_tool_reveals(parts_by_index: dict[int, list[Part]], discovered_tool_names: set[str]) -> None`.
**Data Shape:** A tool return may carry `tools: list[str]` (tool NAMES); executor converts each first occurrence into a `ToolAvailabilityDeltaPart(tools_added=[...], tool_call_id=...)`; run-scoped `discovered_tool_names` accumulates.

### Decisive source
```python
# _tool_execution.py:207-216 — WHY pruning happens at assembly, not per-task
# Tool calls execute concurrently and author their availability deltas at completion time, so
# deduplicating there would tie the emitted history to task scheduling: parallel siblings that
# reveal the same name would race for the delta. Prune at assembly instead, in model call
# (index) order — the first call to name a tool in history owns its reveal...
# Must run exactly once per executor pass: it is not idempotent (a second pass would see every
# name as already discovered and drop the deltas it just kept).

# :193-196 — capability-owned tools must be LOADED, not bare-named
if (capability_id := toolset_tool.tool_def.capability_id) is not None \
        and capability_id != activating_capability_id \
        and capability_id not in run_ctx.available_capability_ids:
    raise exceptions.UserError(f'`ToolReturn.tools` cannot reveal {name!r}: it belongs to '
        f'capability {capability_id!r}, which must be loaded with `load_capability` ...')
```

**Flow:** Tool returns `ToolReturn(return_value=..., tools=['search_web'])` → `build_tool_return_part` validates shape (list of strings; bare string is a UserError) → per-call gate rejects capability-owned names unless that capability is loaded (the loader itself passes via `activating_capability_id`, but stays subject to the rule for OTHER capabilities — no smuggling mid-step) → delta part appended → at assembly, deltas are pruned in index order against `discovered_tool_names`, which is updated in the same pass so the durable set always matches emitted history.
**Invariant:** Reveal ordering is history-deterministic, independent of task scheduling. Bare-name reveals can never activate a capability's side effects (instructions/hooks/settings) — only `load_capability` does. The prune must run exactly once per pass (non-idempotent by design).
**Probe:** `tests/test_tool_availability.py` + `tests/test_tool_availability_portability.py` pin availability/reveal portability across providers.

## Get live surrounding code
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_reject_unloaded_capability_reveals _prune_duplicate_tool_reveals ToolAvailabilityDeltaPart", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt assembly-time reveal dedup + load-before-reveal gating for capability bundles; adapt the delta message part to your history schema; omit cross-provider replay specifics unless you serialize availability across model families. Caveat: none — read at HEAD this session.
