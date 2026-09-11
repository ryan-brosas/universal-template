<!-- capsule-v2 -->
# find_cycle (keys-only DFS cycle detection shared by plan-time and spawn-time)

## Source
pipeshub-ai Apache-2.0 `main@4a02110d`; Codebase Memory `pipeshub-ai`. **Question:** How do two different dependency validators (plan graphs, spawn batches) share ONE cycle detector without disagreeing about dangling edges?

## Path/Symbol
`tools/builtin/coordination/graph_utils.py` — `find_cycle(adjacency: dict[str, list[str]]) -> list[str] | None` (:12–50). Callers: `create_plan._validate_steps` (:116), `critique_plan._validate_structured_plan_against_registry` (:85), `spawn_scheduler` (runtime batch validation).

## Signature
WHITE/GRAY/BLACK three-color DFS with an explicit `stack`; returns the node ids of ONE cycle in order (`[*stack[idx:], successor]` — successor repeated at the end so the loop reads as a cycle) or None.

## Data Shape
Input maps each node to the nodes it DEPENDS ON (successor direction). Only nodes present as KEYS are visited; edges pointing outside the key set are silently SKIPPED.

### Decisive source
```python
Only nodes present as KEYS in ``adjacency`` are visited — edges
pointing to nodes outside the key set (e.g. already-completed tasks
from a prior turn) are silently skipped, matching the spawn scheduler's
existing semantics.
...
for successor in adjacency.get(node, []):
    if successor not in color:
        continue          # dangling edge: NOT an error
    if color[successor] == GRAY:
        idx = stack.index(successor)
        return [*stack[idx:], successor]
```

**Flow:** create_plan validates fresh plans (all deps exist BEFORE find_cycle runs, so keys-only skipping never hides a real error there); spawn_scheduler reuses it on cross-turn batches where deps may legitimately reference ALREADY-COMPLETED task_ids that aren't keys — those must read as "satisfied", not "cyclic". The scheduler's `_find_cycle` (:164–185) is a thin ADAPTER, not a second algorithm: it maps task_ids→call_ids, filters edges to in-batch calls only ("already-completed task_ids ... can never participate in a cycle"), then delegates to the SAME `_shared_find_cycle` (:185).

**Invariant:** Keys-only traversal is LOAD-BEARING, not sloppiness: the same function serves a validator where dangling refs were pre-rejected (plan path) and one where they're expected (spawn path). A porter who "fixes" unknown-node handling to raise will break cross-turn spawn batches; one who drops the pre-check in create_plan loses unknown-dep detection.

**Probe:** No direct unit test for graph_utils itself (coverage caveat): behavior is pinned through its callers — test_create_plan.py (validation errors) and tests/unit/agent_loop_lib/agent/test_spawn_agent_dependencies.py + test_spawn_scheduler.py (cross-turn semantics).

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --semantic-query '["find_cycle","_validate_steps","schedule_spawn_batch"]'
```

## Verdict
Adopt the 25-line three-color detector verbatim (with keys-only semantics documented at the call sites); adapt nothing — this is the rare copy-as-is capsule.
