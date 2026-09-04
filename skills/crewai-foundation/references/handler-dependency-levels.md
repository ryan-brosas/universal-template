<!-- capsule-v2 -->
# Handler dependency levels — how do event handlers declare ordering dependencies while everything else stays parallel?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How do I schedule handlers so declared prerequisites finish first but independent handlers still run concurrently?

## Kahn topological levels + per-event plan cache
**Path/Symbol:** `lib/crewai/src/crewai/events/handler_graph.py` (`HandlerGraph._resolve` :60–92, `build_execution_plan` :105–127); bus integration `event_bus.py:458–523` (`_emit_with_dependencies`), cache invalidation `_register_handler` :243, `off` :399.
**Signature:** `build_execution_plan(handlers: Sequence[Handler], dependencies: dict[Handler, list[Depends[Any]]]) -> ExecutionPlan`.
**Data Shape:** `ExecutionPlan = list[frozenset[Handler]]`; `Depends.__hash__ = id(self.handler)` (identity equality — wrapper instances must be THE registered function).

### Decisive source
```python
remaining = [h for h, deg in in_degree.items() if deg > 0]
if remaining:
    raise CircularDependencyError(remaining)
```
```python
# _emit_with_dependencies: read under r-lock, build under w-lock, double-check
for level in cached_plan:
    level_sync = frozenset(h for h in level if h in sync_handlers)
    level_async = frozenset(h for h in level if h in async_handlers)
    if level_sync: ...submit to sync executor...
    if level_async: await self._acall_handlers(source, event, level_async, state)
```

**Flow:** handlers for one event type with `depends_on=` deps are grouped into levels via BFS (level 0 = no deps; each later level depends only on earlier ones) → within a level, async handlers gather concurrently and sync handlers run as ONE executor task (contextvars copied); levels execute strictly in order → the whole plan is cached per event TYPE and invalidated on any register/unregister (`_execution_plan_cache.pop(event_type, None)` at :243/:399). Events WITHOUT dependencies keep the legacy fast path.
**Invariant:** A cycle raises at PLAN BUILD time (registration-adjacent), not at emit time — a port that defers detection ships deadlocked handlers. Identity-based Depends hashing means redefining a handler function silently breaks dependency linkage. Sync handlers of a level share one submitted job: they are ordered among themselves by set iteration, not concurrency.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/events/test_depends.py" -q` (expect all green incl. ordering + circular rejection).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "handler dependency graph execution plan levels circular", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt eager cycle detection + level-gated parallelism + type-scoped plan caching; adapt the sync-in-executor detail to your runtime; omit dependency support entirely rather than half-porting it — the fast path exists precisely for handler sets without deps. Direct tests executed green at pin.
