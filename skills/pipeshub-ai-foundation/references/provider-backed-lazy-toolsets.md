<!-- capsule-v2 -->
# Provider-backed lazy toolsets — how does a registry expose expensive toolsets without building any Tool until needed?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you make "no full Tool object is built until something needs it" STRUCTURAL rather than conventional?

## Summary-only registration + per-name materialize lock + double-check
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/provider.py:ToolsetProvider/EagerToolsetProvider` (L47–88); `backend/python/app/agent_loop_lib/tools/registry.py:ToolRegistry.register_toolset_provider/materialize/materialize_many` (L181–263).
**Signature:** `ToolsetProvider.summary() -> ToolsetSummary; list_tools() -> list[ToolSummary]` (cheap, pure, no I/O — called on EVERY run's discovery); `await materialize(name) -> Tool` (the expensive work: MCP round trip, remote fetch); `register_toolset_provider(provider)` stores ONLY summaries.
**Data Shape:** Registry state: `_providers{toolset_name → provider}`, `_provider_owner{tool_name → toolset}`, `_provider_tool_summary`, `_materialize_locks{name → asyncio.Lock}` (lazy). Materialized tools move into the ordinary `_tools_by_path`/`_path_by_name` tables.

### Decisive source
```python
async def materialize(self, name: str) -> Tool:
    if name in self._path_by_name:                 # fast path, outside lock
        return self._tools_by_path[self._path_by_name[name]]
    owner = self._provider_owner.get(name)
    if owner is None:
        raise ToolNotFoundError(name)
    lock = self._materialize_locks.setdefault(name, asyncio.Lock())
    async with lock:
        if name in self._path_by_name:             # re-check INSIDE the lock
            return self._tools_by_path[self._path_by_name[name]]
        # two concurrent callers (fetch_tools + search_tools racing the same
        # toolset) would otherwise BOTH materialize and the second register
        # would raise DuplicateToolNameError; the loser gets the winner's tool
        tool = await self._providers[owner].materialize(name)
        self.register_tool(tool)                   # cached like an eager tool
        return tool

async def materialize_many(self, names) -> None:
    """Call this BEFORE adding provider-backed names to agent.visible_tools —
    once a name is visible, the turn loop resolves its schema SYNCHRONOUSLY,
    so materialization can't happen lazily at that point."""
```

**Flow:** register provider (summaries only) → discovery/search render summaries with zero builds → first real need (`fetch_tools`, preloading, visible-tool grant after `materialize_many`) → per-name lock → build once → ordinary registration → every later resolve is a sync dict lookup.
**Invariant:** (1) The Protocol omits a `tools` property ENTIRELY so eagerness is impossible by construction — narrower-than-Toolset is the point. (2) Per-name locks + inside-lock re-check make concurrent first-touch idempotent. (3) `materialize_many` before visibility is a hard ordering rule: schema resolution for visible tools is synchronous. (4) A provider handing back a colliding path/name raises duplicate errors = provider bug (it advertised that exact name via `list_tools()`).
**Probe:** `tests/unit/agent_loop_lib/tools/test_registry.py::test_register_toolset_provider_exposes_summary_without_materializing` (:128), `::test_materialize_builds_and_caches_the_real_tool` (:151), `::test_concurrent_materialize_calls_for_same_name_only_build_once` (:222), `::test_materialize_many_skips_plain_and_already_materialized_names` (:165); wiring-level: `tests/unit/agent_loop_lib/tools/test_lazy_toolsets.py::test_provider_backed_toolset_is_materialized_before_fetch_returns` (:158).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ToolsetProvider EagerToolsetProvider register_toolset_provider materialize _materialize_locks", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the summary-first protocol + locked double-checked materialization for any plugin/MCP tool surface with expensive discovery; adapt cache policy. Omit the concrete MCP provider (deliberately not shipped in-module). Direct tests cover summary-vs-build split, caching, concurrency, and fetch integration at HEAD.
