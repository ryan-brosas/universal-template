<!-- capsule-v2 -->
# DAG validation via Kahn's algorithm — How do you prove a task graph is executable before running it?

**Source:** ufo (MIT) `main@96983c73ed09`; Codebase Memory `ufo`. **Question:** What minimal checks certify a dependency graph is acyclic and referentially sound, and what shape should the error report take?

## Topological-sort-as-validation + dangling endpoint scan
**Path/Symbol:** `galaxy/constellation/task_constellation.py:TaskConstellation.validate_dag` (:483-506), `has_cycle` (:1181-1187), `get_topological_order` (:508-547).
**Signature:** `def validate_dag(self) -> Tuple[bool, List[str]]`.
**Data Shape:** `_tasks: Dict[str, TaskStar]`, `_dependencies: Dict[str, TaskStarLine]` where each line has `from_task_id`/`to_task_id`; returns `(is_valid, list_of_error_strings)` — never throws for an invalid graph.

### Decisive source
```python
def validate_dag(self) -> Tuple[bool, List[str]]:
    errors = []
    if self.has_cycle():
        errors.append("DAG contains cycles")
    for dependency in self._dependencies.values():
        if dependency.from_task_id not in self._tasks:
            errors.append(
                f"Dependency references non-existent source task {dependency.from_task_id}")
        if dependency.to_task_id not in self._tasks:
            errors.append(
                f"Dependency references non-existent target task {dependency.to_task_id}")
    return len(errors) == 0, errors

def has_cycle(self) -> bool:
    try:
        self.get_topological_order()
        return False
    except ValueError:
        return True
```
Cycle detection inside `get_topological_order` is Kahn's algorithm; its exit test:
```python
if len(result) != len(self._tasks):
    raise ValueError("DAG contains cycles")
```

**Flow:** attempt a full Kahn topological sort (in-degree table over all tasks → process zero-in-degree queue → decrement neighbors); if the sorted output misses any task id, a cycle exists → separately verify every edge references tasks that exist → aggregate all problems into one string list so a planner can repair everything in one round.
**Invariant:** validation must be exception-free toward callers (errors are data), and cycle detection must consider *every* task node even those with no edges (they seed in-degree 0).
**Probe:** `validate_dag` has 17 inbound callers in the codebase (orchestrator `_validate_and_prepare_constellation`, serialization, agent tooling); direct-test caveat: no dedicated upstream unit suite for `validate_dag` was found at this pin — behavior pinned by source read + caller inspection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ufo", query: "validate dag topological order has cycle", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt "topological sort succeeds ⇒ acyclic" as the cycle oracle and collect dangling-edge errors alongside instead of failing fast. Adapt error strings into structured error objects if your planner consumes them programmatically. Omit UFO's adjacency defaultdict rebuild per call if you need incremental validation on large graphs — this implementation re-sorts from scratch every invocation.
