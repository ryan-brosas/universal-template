<!-- capsule-v2 -->
# Tracker-first combined tool provider — how do you merge runtime-captured tools with registry tools, and when does the cache invalidate?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How does one provider serve both live tracker tools (learned mid-session) and registry MCP tools, and what exactly clears the tools cache?

## CombinedToolProvider
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/providers/combined.py:200-456` (`CombinedToolProvider.initialize/get_apps/get_tools/get_all_tools/reset/_filter_tools_by_include`), tracker tool factory :29-194 (`create_tool_from_tracker`).
**Signature:** `async get_tools(self, app_name: str) -> List[StructuredTool]`; `async get_apps(self) -> List[AppDefinition]`; `get_include_by_app: Callable[[], Tuple[Optional[Dict[str, List[str]]], int]]`.
**Data Shape:** `tools_cache: Dict[app_name, List[StructuredTool]]`; `_last_include_version: int` gates cache validity.

### Decisive source
```python
if self.get_include_by_app:
    include_by_app, version = self.get_include_by_app()
    if version != self._last_include_version:
        self._last_include_version = version
        self.tools_cache.clear()          # policy edit ⇒ FULL cache invalidation

if app_name in self.tools_cache:
    cached = self.tools_cache[app_name]
    if self.get_include_by_app:
        # cached list is the FULL list; include-filter applied per READ
        include_ids = ...
        if include_ids is not None and len(include_ids) > 0:
            return self._filter_tools_by_include(cached, app_name, include_ids)
    return cached
```
Error contract in the tracker tool (:139-148):
```python
except asyncio.TimeoutError:
    raise TimeoutError(...)      # timeout is the ONE error that propagates
except Exception as e:
    return {"error": error_msg}  # everything else is data the model can read
```

**Flow:** apps always re-fetched fresh (cheap; "services that became ready after startup are picked up automatically") while TOOLS stay cached (heavy) → per-app load: tracker tools first, registry HTTP second with first-wins dedup by name → include-list filtering applied at read time over the full cached set → version bump on the include callable clears the whole cache.
**Invariant:** (1) apps are cheap-and-fresh, tools are expensive-and-cached — flipping that is the classic porting mistake that either freezes late-starting servers out or hammers the registry; (2) the cache stores UNFILTERED tool lists; scoping is a read-time projection so include edits don't require reloads (only version-bump clears); (3) tool errors are returned as `{"error": ...}` data EXCEPT timeouts which must interrupt the block; sync invocation while a loop runs raises instead of deadlocking (`asyncio.get_running_loop()` probe); unhashable list defaults are dropped to None rather than crashing `create_model`.
**Probe:** no direct unit test for this provider (coverage caveat — deterministic checks: bump version ⇒ next get_tools misses cache; duplicate name across tracker+registry ⇒ tracker's wins; non-timeout failure returns dict not exception). Registry-side arg validation is tested in `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_registry_provider_arg_validation.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "CombinedToolProvider get_include_by_app tools_cache", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fresh-apps/cached-tools split and read-time filtering over full caches; adopt the error-as-data-except-timeout contract for model-invoked tools; adapt include-version plumbing to your policy store; omit the tracker leg if your runtime has no learned-tools surface. Coverage caveat: source-read verified; sibling provider's validation path directly tested.
