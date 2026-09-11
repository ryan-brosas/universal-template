<!-- capsule-v2 -->
# require_critique (spawn-tree-shared pending gate via by-reference StateSlot)

## Source
pipeshub-ai `main@4a02110d` — `hooks/middleware/builtin/require_critique.py` (whole file, 153L).

## Path/Symbol
- `_CritiqueState` — mutable holder with `.pending: bool` (:48)
- `PENDING_CRITIQUE: StateSlot[_CritiqueState] = StateSlot(key="require_critique.state", default_factory=..., inherit=True)` (:58)
- `require_critique(confidence_threshold=Confidence.HIGH) -> _install(kernel)` (:80)
- `_ALWAYS_ALLOWED_SUFFIXES` (:74), `_CONFIDENCE_RANK` (:64)

## Signature
Returns an INSTALLER (not a middleware): `_install(kernel)` registers a PRE_TOOL_USE + POST_TOOL_USE pair; idempotent per closure via a `marker = object()` recorded in `kernel._require_critique_installed`.

## Data Shape
POST_TOOL_USE: `/create_plan` success → `pending = rank(confidence) < rank(threshold)`; `/critique_plan` success with `data["passed"]` truthy → `pending = False`. PRE_TOOL_USE: while pending, deny every tool whose path doesn't end in the planning/escalation suffix set.

## Decisive source
```python
PENDING_CRITIQUE: StateSlot[_CritiqueState] = StateSlot(
    key="require_critique.state", default_factory=_CritiqueState, inherit=True,
)
# run_child() propagates the parent's scope, and inherit=True copies the
# holder BY REFERENCE — the whole spawn tree shares one pending bucket.
```

## Invariant
**The whole spawn tree shares ONE pending-critique bucket** (by-reference inherited mutable object): a child spawned mid-pending is blocked too, and a passing critique ANYWHERE clears it for everyone. A per-run bool would silently drop that. `task_complete` is deliberately NOT in the allowlist — finishing on an unreviewed plan is exactly what this gate exists to prevent. Distinct from supervisor_confidence_gate (which blocks one LOW result, always-on); this one denies execution until re-review.

## Probe
`tests/unit/agent_loop_lib/hooks/middleware/builtin/test_require_critique.py`: install idempotence :65, two independent installs :73, deny + short-circuit :95/:107, suffix bypass :127, **`test_task_complete_is_not_in_the_allowlist` :137**, state-transition matrix :158–268, full cycle :282.

## Retrieve
`codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["require_critique","PENDING_CRITIQUE","critique_plan"]'`

## Verdict
ADOPT. The exemplar for migrating hook state off session-keyed dicts onto StateSlots without losing spawn-tree sharing semantics — and for installer-style (closure-marker-idempotent) registration.
