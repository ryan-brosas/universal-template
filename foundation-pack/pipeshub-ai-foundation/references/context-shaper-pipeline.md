<!-- capsule-v2 -->
# Context shaper pipeline (L1–L8 cheapest-first composition)

## Source
pipeshub-ai `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`
(`backend/python/app/agent_loop_lib/control_plane/config.py`, `control_plane.py`; platform twin `app/agents/agent_loop/factory.py`).

## Path/Symbol
- `ContextEngineConfig` (config.py :22–75) — per-layer enable flags + knobs, docstring pins the layer order.
- `ControlPlane.start()` context-engine block (control_plane.py :609–650) — wires each enabled shaper onto `HookEvent.PRE_MODEL` **in list order**.
- Platform adapter overrides the tail: `factory.py :770–793` wires L4/L5/L6, then TWO `shape_auto_compact` instances (L7a `_AUTO_COMPACT_PHASE1_TAIL_RATIO`, L7b PHASE2), then L8 `shape_synthesis_guard()` and **L9 `shape_tool_pairing_repair()`** — the pairing net is added by the adapter, not ControlPlane.

## Signature
Each shaper is `def shape_<name>(...) -> async fn(ctx: ModelCallContext, next_fn)`; registered via `kernel.on(HookEvent.PRE_MODEL).use(...)`; each mutates `ctx.messages` then awaits `next_fn()`.

## Data Shape
Order (config.py :26–33): L1 budget_reduction → L2 artifact_compaction → L3 tool_result_clearing → L4 loop_compaction → L5 sliding_window → L6 deterministic_compact → L7 auto_compact (LLM summarizer) → L8 synthesis_guard. POST_TOOL_USE: artifact_registration.

## Decisive source
```python
# control_plane/config.py
PRE_MODEL shapers run cheapest-first:
    L1 budget_reduction ... L7 auto_compact (LLM summariser, last resort)
    L8 synthesis_guard   (hard budget enforcement)
```
```python
# control_plane/control_plane.py :609+
if ce.enable_budget_reduction:
    kernel.on(HookEvent.PRE_MODEL).use(shape_budget_reduction(...))
if ce.enable_artifact_compaction:
    kernel.on(HookEvent.PRE_MODEL).use(shape_artifact_compaction(...))
...
if ce.enable_synthesis_guard:
    kernel.on(HookEvent.PRE_MODEL).use(shape_synthesis_guard(...))
```

## Flow
Every model call walks the PRE_MODEL pipeline in registration order. Cheap deterministic caps run first so expensive layers (LLM summarizer) see already-shrunk input; the hard guard runs last so it measures the post-shaper size. Each layer is independently toggleable; flags default True except `enable_offload`/`enable_auto_compact` style extras which are config-gated.

## Invariant
**Cheapest-first ordering is load-bearing**: an LLM-summarizing layer must never run before deterministic reduction, and the raising guard (`synthesis_guard`) must be the LAST shaper — anything after it would re-inflate a context that was already forced under budget. Registration order == enforcement order because the kernel preserves `.use()` order.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_context_compaction.py::test_passes_when_under_budget` (:281) and `test_raises_on_unresolvable_overflow` (:271) pin the tail behavior of the pipeline's last enforced layer; `tests/unit/agent_loop_lib/control_plane/test_control_plane_coverage.py::test_context_engine_hook_default_subflags` (:268) pins that default subflags register the expected shaper set.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["ContextEngineConfig","shape_synthesis_guard","PRE_MODEL"]'`

## Verdict
ADOPT. Port the layer *ladder* and its order, not any single shaper: the design claim is that context fitting is a cascade of increasingly-lossy cheap→expensive passes ending in a fail-loud guard.
