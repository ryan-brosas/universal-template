<!-- capsule-v2 -->
# Handler dependency graph — Kahn levels with cached execution plans and aemit bypass

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** How do `depends_on` handlers execute in dependency order while independent ones stay parallel — and where does the plan cache invalidate?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/events/handler_graph.py` — `HandlerGraph._resolve` (:60), `build_execution_plan` (:105); consumer `event_bus.py:_emit_with_dependencies` (:458-522).
**Signature:** `HandlerGraph(handlers: dict[Handler, list[Depends]]) -> None` (resolves in ctor); `build_execution_plan(handlers, dependencies) -> ExecutionPlan` (list of level sets); raises `CircularDependencyError(remaining_handlers)`.
**Data Shape:** BFS-by-waves topological sort: in_degree map + dependents adjacency; each wave = one parallel-executable level appended to `self.levels`.

### Decisive source
```python
# :60 _resolve — classic Kahn; leftover in-degree > 0 IS the cycle report
queue: deque[Handler] = deque([h for h, deg in in_degree.items() if deg == 0])
while queue:
    current_level: set[Handler] = set()
    for _ in range(len(queue)):          # freeze the wave size
        handler = queue.popleft()
        current_level.add(handler)
        for dependent in dependents[handler]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)
    if current_level:
        self.levels.append(current_level)
remaining = [h for h, deg in in_degree.items() if deg > 0]
if remaining:
    raise CircularDependencyError(remaining)

# event_bus :489 — read-lock fast path, write-lock build-once cache
with self._rwlock.r_locked():
    cached_plan = self._execution_plan_cache.get(event_type)
if cached_plan is None:
    with self._rwlock.w_locked():
        if cached_plan is None:                    # double-check inside
            cached_plan = build_execution_plan(all_handlers, dependencies)
            self._execution_plan_cache[event_type] = cached_plan
```

**Flow:** register handler (possibly with `Depends`) → first emit of that type builds levels under write lock (double-checked) → every dispatch walks level-by-level: within a level sync handlers run sequentially on the pool thread and async handlers gather concurrently; next level starts only when the previous completes. Handler set changes drop the cache (rebuilt lazily). `aemit` intentionally IGNORES dependency ordering (:261 test) — async-native emission trades ordering for non-blocking.
**Invariant:** Cycle detection is implicit: anything left with in_degree>0 after the waves is reported BY NAME in CircularDependencyError. The plan cache lives behind the rwlock's writer double-check so two concurrent first-emits cannot both build. Levels are SETS — no cross-handler order guarantees within a level.
**Probe:** `grep -c 'CircularDependencyError' lib/crewai/src/crewai/events/handler_graph.py` → `3`; direct suite: `/tmp/crewai-p1-venv/bin/python -m pytest tests/events/test_depends.py -q -p no:xdist -o addopts=''` → `10 passed`.
**Direct test:** `tests/events/test_depends.py::test_basic_dependency` (:19), `::test_circular_dependency_detection` (:195), `::test_aemit_ignores_dependencies` (:261).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "HandlerGraph resolve dependencies into parallel execution levels", limit: 5 });
// → ext-crewAI...events.handler_graph.HandlerGraph._resolve Method 60-92
```

## Verdict
Adopt Kahn-levels + double-checked plan cache + explicit aemit-bypass. Adapt Depends typing to host DI. Omit CrewAI's ExecutionPlan TypedDict aliases.
