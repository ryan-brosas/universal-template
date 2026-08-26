<!-- capsule-v2 -->
# ToolGuard invoker bridge — how guard validation executes the agent's REAL tools without recursing into guarded wrappers

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When generated guard code needs to call a tool to validate policy behavior, what contract must that execution path honor so validation sees real behavior and cannot loop or misroute?

## The provider-side invoker handed to toolguard's runtime
**Path/Symbol:** `src/cuga/backend/cuga_graph/policy/tool_guard/tool_invoker.py` (`ToolGuardInvoker(IToolInvoker)` :17, `_get_tools` :42-71, `invoke` :73-123, `clear_cache` :125-133).
**Signature:** `async invoke(self, toolname: str, arguments: Dict[str, Any], return_type: Type[T]) -> T`; constructed once as `ToolGuardInvoker(tool_provider)` inside `ToolGuardRuntime.__init__` (tool_guard_runtime.py :62) and reused for every guard evaluation.
**Data Shape:** `_tools_cache: Optional[Dict[name, tool]]` built lazily from `get_all_raw_tools()` when present else `get_all_tools()` — the RAW surface is load-bearing (the sibling capsule `provider-decorator` explains why: guarded wrappers would recurse).

### Decisive source
```python
# tool_invoker.py:52-67 — duplicate names are a routing hazard, not a warning
if self._tools_cache is None:
    if hasattr(self.tool_provider, "get_all_raw_tools"):
        tools_list = await self.tool_provider.get_all_raw_tools()
    else:
        tools_list = await self.tool_provider.get_all_tools()
    # Check for duplicate tool names before building cache
    tools_map: Dict[str, Any] = {}
    for tool in tools_list:
        if tool.name in tools_map:
            raise ValueError(
                f"Duplicate tool name detected: '{tool.name}'. "
                f"Tool names must be unique across all providers to ensure "
                f"correct routing of guards to tools.")
```

**Flow:** guard code (generated at build time, see `toolguard-manager`) runs under toolguard's umbrella module; when it calls a tool through the injected `IToolInvoker`, `invoke()` logs only arg KEYS with value TYPES redacted (`f"<{type(v).__name__>}>"`, never values), resolves the tool from the lazy cache, raises `ValueError` listing available names on a miss, executes via LangChain's `await tool.ainvoke(arguments)`, and funnels every non-Cancelled exception into `RuntimeError(f"Tool invocation failed for '{toolname}': ...") from e`. `except ValueError: raise` and `except asyncio.CancelledError: raise` pass both classes through untouched.
**Invariant:** name→tool resolution must be UNIQUE and STABLE during a guard run — duplicate names raise at cache-build time because guards route by bare name; cancellation must never be swallowed (a cancelled guard must cancel, not report a violation); sensitive argument VALUES never reach logs.
**Probe:** no dedicated unit suite at HEAD — behavior pinned indirectly by the runtime ladder tests in `tests/unit/test_toolguard_provider.py` (guard execution paths) and by `cuga_graph/policy/tool_guard/tool_guard_runtime.py` consumers; treat this file as source-read-verified (coverage caveat).
**Retrieve:**
```python
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ToolGuardInvoker invoke", limit: 5 });
```

## Verdict
Adopt the raw-tools + duplicate-name-raise + key-only logging + CancelledError passthrough contract verbatim whenever porting runtime policy validation onto an existing tool provider. Adapt `ainvoke` to your host's execution primitive. Omit nothing — the ValueError re-raise distinction (routing error vs execution failure) is what lets callers classify failures. Cross-reference: block/allow decision ladder lives in `toolguard-runtime.md`.
