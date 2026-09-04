<!-- capsule-v2 -->
# Tool cache opt-in — crew-level cache handler offered to agents, default re-execution

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** When do identical tool calls dedupe vs re-execute — and how does the manager agent join the caching scheme?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/tools/tool_usage.py` (cache hit path) + `crew.py` wiring (`_create_manager_agent` :1543-1548); behavior tests `tests/test_tool_cache_default.py`.
**Signature:** crew `cache: bool = True` field → `_cache_handler` shared into agents via `agent.set_cache_handler(self._cache_handler)`; standalone agents get NO handler by default.
**Data Shape:** CacheHandler = key(function name + serialized args) → cached output; hit returns without execution.

### Decisive source
```python
# :1544 manager joins the cache scheme OUTSIDE the agents loop — comment verbatim:
# "The manager is created outside the agents loop that offers the
#  crew's cache handler at validation time; offer it here so an
#  opted-in crew (cache=True) also dedupes the manager's tool calls."
if self.cache:
    manager.set_cache_handler(self._cache_handler)
```

**Flow:** Crew(cache=True, default) → each agent receives the shared handler at setup → identical (tool,args) within the run returns the memoized result → standalone `Agent(...)` has no handler ⇒ every call re-executes unless explicitly opted in (`cache=True`). Test matrix pins all four quadrants (default-reexecute / crew-dedupe / standalone-default-off / explicit-opt-in).
**Invariant:** The DEFAULT for crews is dedupe-ON but for bare agents OFF — a porter flipping either default changes replay/determinism semantics of every run. Manager must be handed the handler separately because it's constructed after the per-agent loop.
**Probe:** `grep -c 'def test_default_reexecutes_identical_tool_calls' lib/crewai/tests/test_tool_cache_default.py` → `1`.
**Direct test:** `tests/test_tool_cache_default.py::test_default_reexecutes_identical_tool_calls` (:131), `::test_crew_cache_true_dedupes_identical_tool_calls` (:136), `::test_standalone_agent_has_no_cache_by_default` (:151).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "set_cache_handler crew cache handler manager agent tools", limit: 5 });
// → ext-crewAI...crew.Crew._create_manager_agent Method 1518+; tools.tool_usage tool cache paths
```

## Verdict
Adopt opt-in-shared-handler caching with explicit defaults documented. Adapt cache key serialization. Omit CacheHit/CacheMiss event payloads.
