<!-- capsule-v2 -->
# Provider Decorator — enforcing policy at the tool-provider boundary so every tool source is covered once

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Where should runtime tool enforcement wrap in — per node, per call, or the provider — and how do you avoid double-wrapping and guard-recursion?

## ToolGuardingToolProvider + raw-tool escape hatch
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/providers/toolguard.py` (`ensure_wrapped` :39-62, `get_tools` :108-113, `get_raw_tools`/`get_all_raw_tools` :123-133, `configure` :166-189, `invalidate_toolguard_runtime` :199-212, `_wrap_tool` :250-323, helpers :377-419).

**Signature:** `ensure_toolguard_provider(provider, *, policy_storage=None, cuga_folder=".cuga", enabled=True) -> ToolGuardingToolProvider`.

**Data Shape:** Wraps any `ToolProviderInterface`; guarded tools are fresh `StructuredTool`s (sync+coroutine pair) carrying copied metadata attrs (`_app_name`, `_operation_id`, `_param_constraints`, `_response_schemas`) with `_app_name` defaulted from the wrapping app. Wrapper cache: `_guarded_tools_cache[(app, name, id(tool))]`; runtime behind an `asyncio.Lock`, lazily created.

### Decisive source
```python
# toolguard.py:39-55 — idempotent wrap (no double layering)
@classmethod
def ensure_wrapped(cls, provider, *, policy_storage=None, cuga_folder=".cuga", enabled=True):
    if isinstance(provider, cls):
        provider.configure(policy_storage=policy_storage, cuga_folder=cuga_folder, enabled=enabled)
        return provider
    return cls(provider, ...)
# toolguard.py:298-306 — sync-in-async-loop rejection instead of silent deadlock
def guarded_tool_func_sync(*args, **kwargs):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(guarded_tool_func(*args, **kwargs))
    raise RuntimeError(
        f"ToolGuard-wrapped tool '{tool_name}' was invoked synchronously while an event loop is running. "
        "Use ainvoke() for async execution.")
```
Blocked-call payload (:284-291): `{"error": "Tool call blocked by policy: ...", "blocked_by_policy": True, "policy_violation": True, "tool": ..., "app": ...}`.

**Flow:** graph/SDK builds base provider → `ensure_toolguard_provider` wraps once → nodes request tools and get wrappers → model calls a wrapper → args normalized against schema param names (unexpected ⇒ tracked error result) → runtime guard → original `tool.ainvoke` on allow. Guard code that needs helper tools calls `invoker`, which prefers `get_all_raw_tools()` so delegates never re-enter guarded wrappers. Any mutation path (`add_tool(s)`, `reset`, `configure` with changed storage/folder/enabled flag, SDK `update_tool_guard`) calls `invalidate_toolguard_runtime()` — synchronous by design so SDK code without a loop can call it — dropping cached runtime + wrappers so next invocation re-reads policies.

**Invariant:** One enforcement seam at the provider means registry tools, direct LangChain tools (app `"runtime_tools"`), and tracker tools are all governed without per-node code; but the escape hatch must exist because guard→delegate→guarded-wrapper recursion would otherwise infinitely re-enter the same policy check. The cache-key includes `id(tool)` precisely because base providers swap tool objects; stale caches after policy edits would enforce deleted guards.

**Probe:** `tests/unit/test_toolguard_provider.py:125 delegates_and_exposes_raw_tools`, `:147 is_transparent_without_policy_storage`, `:160 allows_when_runtime_allows`, `:186 blocks_without_calling_original_tool` (asserts the original tool was NOT invoked), `:342 ensure_toolguard_provider_wraps_and_reconfigures_without_double_wrapping`, `:443 guards_disabled_skips_registration`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "ToolGuardingToolProvider ensure_wrapped get_all_raw_tools invalidate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt decorator-at-the-boundary with idempotent ensure/configure, raw-tool delegate APIs, sync-in-loop rejection, and mutation-triggered invalidation. Adapt the StructuredTool construction to your framework's tool type. Omit the tracking integration (`ToolCallTracker.record_call`) if you have separate observability.
