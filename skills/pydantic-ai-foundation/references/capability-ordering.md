<!-- capsule-v2 -->
# Capability ordering — topological middleware tiers from declarative constraints

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How do you let each middleware declare "I must wrap X" / "Y wraps me" without hand-ordering the whole chain?

## sort_capabilities
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/capabilities/_ordering.py:sort_capabilities` (:17-36), `_add_position_edges` (:85-103), `_add_relative_edges` (:106-125), `CapabilityOrdering` (abstract.py :117-158).
**Signature:** `sort_capabilities(capabilities: Sequence[AbstractCapability]) -> list[AbstractCapability]`; `CapabilityOrdering(position: 'outermost'|'innermost'|None, wraps: Sequence[CapabilityRef], wrapped_by: Sequence[CapabilityRef], requires: Sequence[type])`.
**Data Shape:** Refs match by TYPE (`issubclass` against any leaf's class) or INSTANCE (identity `is`); container capabilities merge orderings across ALL leaves, erroring on conflicting positions.

### Decisive source
```python
# _ordering.py:70-80 — original order is the TIEBREAKER; edges only constrain
ts: TopologicalSorter[int] = TopologicalSorter()
for i in range(n):
    ts.add(i)                      # insertion order = tiebreak for unconstrained nodes
_add_position_edges(ts, n, orderings)
_add_relative_edges(ts, n, orderings, leaf_types, cap_leaves)
try:
    sorted_indices = list(ts.static_order())
except CycleError:
    raise UserError('Circular ordering constraints among capabilities')

# _ordering.py:116-125 — edge direction encodes wrap semantics: outer comes FIRST
# wraps=[X] → I come before X
for ref in ordering.wraps:
    ...
    ts.add(j, i)
# wrapped_by=[X] → X comes before me
for ref in ordering.wrapped_by:
    ...
    ts.add(i, j)
```

**Flow:** Collect leaves per top-level capability → merge effective orderings (position conflict inside one tree ⇒ UserError) → validate `requires` (each named type must exist SOMEWHERE in the chain, no order implied) → build graph with position-tier edges (every outermost member before every non-member; innermost after) + relative wrap edges → static topological order; cycles and unmet requires surface as UserErrors naming the constraint. Downstream, first-sorted = outermost wrapper for both hook chaining AND `get_wrapper_toolset` composition; `innermost` capabilities (durability) bind in a SECOND phase after other toolsets exist, at the cost of being unable to contribute toolsets themselves.
**Invariant:** Sorting is total and deterministic for identical inputs (insertion-order tiebreak); a capability with NO constraints keeps its user-given relative position. Instance refs break silently if the target returns a fresh instance from `for_run()` — type refs are the safe default for per-run-stateful targets.
**Probe:** `tests/test_capabilities.py::test_ordering_outermost` (:15844), `::test_ordering_both_outermost_and_innermost` (:15856), `::test_ordering_outermost_tier_with_wraps` (:15889), `::test_innermost_binds_after_capability_toolsets` (:15925), `::test_ordering_requires_present` (:15978).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "sort_capabilities CapabilityOrdering topo_sort innermost", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt declarative ordering constraints resolved by stable topological sort with insertion tiebreak; adapt the tier names; omit two-phase binding if your host has no durability layer needing last-bind semantics. Caveat: source read at HEAD this session.
