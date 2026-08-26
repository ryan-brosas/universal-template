<!-- capsule-v2 -->
# Durable toolset registry — id-keyed wrapper identity, same-instance reuse, and collision refusal

## Source / Question
`pydantic_ai_slim/pydantic_ai/durable_exec/_base.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Durable engines wrap each executing leaf toolset so its I/O becomes checkpointed units identified by a stable id — how do you register wrappers exactly once per toolset even when one instance appears in several places in the tree, and refuse ids that would silently reroute calls? A porter will register duplicates per occurrence or let a second toolset hijack an existing id.

## Path / Symbol
`_base.py` — `_register_toolsets` (:221–224), `_wrap_and_register_leaf` (:226–262), `get_wrapper_toolset` (:268–280), `get_ordering` (:282–285), `get_serialization_name` (:287–293), abstract `_wrap_leaf_toolset` (:264–266).

## Signature
```python
def _wrap_and_register_leaf(self, ts: AbstractToolset) -> AbstractToolset
def get_wrapper_toolset(self, toolset: AbstractToolset) -> AbstractToolset | None   # None = no swap needed
def get_ordering(self) -> CapabilityOrdering   # position='innermost'
```

## Data Shape
Registry `_toolsets_by_id: dict[str, WrapperToolset]` on the bound copy (reset in `for_agent`). Three leaf outcomes at registration: id-less DynamicToolset → loud `UserError` teaching all four id sources (`DynamicToolset(id=...)`, capability `id`, explicit wrap; bare capability functions can't carry ids); id already registered → reuse the SAME wrapper if `existing.wrapped is ts`, else raise (a distinct instance under a taken id "would silently replace it in the registry and route both toolsets' calls to one wrapper"); engine's `_wrap_leaf_toolset` returns None → pass through unwrapped.

### Decisive source — visit-and-replace swap keyed on id (:274–280)
```python
def swap(ts):
    ts_id = ts.id
    if ts_id is not None and ts_id in self._toolsets_by_id:
        return self._toolsets_by_id[ts_id]
    return ts
return toolset.visit_and_replace(swap)
```
`get_ordering()` pins the durability capability `'innermost'`: durable dispatch must be the LAST wrapper around the model handler so every other capability's contribution applies INSIDE the durable unit. `get_serialization_name()` returns `None` — deliberately not spec-loadable because models/handlers/configs aren't spec-serializable and worker setup must construct units.

**Flow:** bind → walk agent toolsets with `visit_and_replace(_wrap_and_register_leaf)` → wrappers index by id → per-run, `get_wrapper_toolset` first runs the runtime-toolset rejection then swaps leaves for their wrapped versions by id.

**Invariant:** One wrapper instance per (engine, toolset id); registration happens once at bind time, never per run; innermost ordering is load-bearing.

**Probe:** `tests/test_dbos.py::test_toolset_without_id` (:905 — FunctionToolset allowed id-less under DBOS), `test_mcp_toolset_without_id` (:910 — MCP requires id because step names + cache keys derive from it), `test_capability_contributed_toolset_id_from_capability` (:924, #6334 regression), `test_capability_contributed_toolsets_with_colliding_derived_id` (:959); `tests/test_temporal.py::test_temporal_wrapper_visit_and_replace` (:2574).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query '_wrap_and_register_leaf _toolsets_by_id get_wrapper_toolset visit_and_replace'
```

## Verdict
**Adopt** the id-keyed registry with same-instance reuse, distinct-instance collision refusal, id-source teaching errors, and innermost ordering. **Adapt** what your wrapper does per leaf. **Omit** the spec-loadability veto if your config format has no spec loader.
