<!-- capsule-v2 -->
# In-process LangChain tool provider — how do you embed agent tools directly (no HTTP/MCP) and what must validation backfill for CodeAct compatibility?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** You're embedding the agent as a library with caller-supplied StructuredTools — what's the provider contract, and why does a StructuredTool missing `.func` need silent repair?

## One virtual app ("runtime_tools"); constructor-time validation; .func backfilled from coroutine/_run
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/providers/langchain.py` — `DirectLangChainToolsProvider(tools=None, app_name="runtime_tools")` :18-49, `_validate_tools` :51-72 (the backfill), `initialize` :73-85, `get_apps` :87-103 (`AppDefinition(name, url=None, description=f"Runtime LangChain tools ({n} tools)", type="langchain")`), `get_tools(app_name)` :105-121 (name mismatch ⇒ warn + []), `add_tool(s)` :134-153.
**Signature:** implements `ToolProviderInterface` (`providers/base.py`): `async initialize()`, `async get_apps() -> list[AppDefinition]`, `async get_tools(app_name) -> list[StructuredTool]`, `async get_all_tools()`; plus sync `add_tool/add_tools` for post-init registration.
**Data Shape:** tools returned BY REFERENCE (the caller's objects, not copies) — metadata enrichment elsewhere must deep-copy before mutating (see tool-guide capsule).

### Decisive source
```python
# :63-71 — CodeAct compatibility repair: generated code calls tools as plain
# awaitables, which needs .func present even for async-only tools
if isinstance(tool, StructuredTool) and not hasattr(tool, "func"):
    logger.warning(f"StructuredTool '{tool.name}' is missing .func attribute. "
                   f"Adding it for CodeAct compatibility.")
    if hasattr(tool, "coroutine") and tool.coroutine:
        tool.func = tool.coroutine      # async tool: func := coroutine fn
    elif hasattr(tool, "_run"):
        tool.func = tool._run           # legacy: func := bound sync run
```
**Flow:** construct → validate each entry is a named BaseTool (raise ValueError with index otherwise) + backfill `.func` → initialize logs count (empty = warning not error) → `get_apps` yields exactly ONE virtual app so downstream app-name matching (incl. `runtime_tools` special-case in guide enrichment) works unchanged vs remote providers → lazy init on first accessor if skipped.
**Invariant:** (1) App-name is exact-match — wrong name returns [] with a warning, never raises (embedded callers may probe). (2) Validation happens in the CONSTRUCTOR (fail fast at wiring time), initialization is idempotent. (3) The `.func` backfill mutates the CALLER's tool object deliberately — document it; it's what lets make_tool_awaitable wrap async-only tools uniformly.

**Probe:** No direct unit suite at HEAD for this provider (coverage caveat — exercised via runtime-tools injection suites around `cuga_agent_core/tools/runtime_tools.py` and e2e embedding examples); source-read verified at pinned commit.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "DirectLangChainToolsProvider get_apps runtime_tools add_tool", limit: 8 });
```
## Verdict
Adopt for embedded/library deployments of an agent that normally loads remote tool catalogs — same interface, zero transport. Keep the backfill + fail-fast validation pair.
