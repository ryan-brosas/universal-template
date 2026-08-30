<!-- capsule-v2 -->
# MCP schema flattening + include filtering — why resolve `$defs` into dotted names, and why must the include filter run at BOTH list and register time?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** MCP tools advertise JSON-Schema inputs with nested objects and `$ref` trees that LLMs mangle — how do you flatten them safely, and what happens when `include:` names a tool the server doesn't actually expose?

## Recursive $defs flattener with string-fallbacks + dual-site include filter
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/mcp_manager.py` — `_flatten_tool_parameters` :1033-1051 (try/except returns ORIGINAL schema on failure), `_flatten_schema_recursive` :1053-1126; include filter at list time :769-782 (`schemas[name]["tools"]` comprehension) and again per-tool at registration :784-786; unmatched-include warning :821-827.
**Signature:** `_flatten_schema_recursive(schema: dict, defs: dict) -> dict`. Rules: skip `$defs` key in output (kept only as resolution source); `#/$defs/Name` refs → inline recursive expansion; UNRESOLVABLE ref → `{"type": "string", "description": f"Reference to {name}"}` (never drop the field); array-of-$ref items → array-of-strings with description `"Array of {Name} objects (simplified to strings)"`; nested object WITH properties → hoist children to parent as `f"{key}_{child}"` prefixed keys; unflattenable object → string leaf.
**Data Shape:** Input `inputSchema` (JSON Schema w/ optional `$defs`); output flat properties dict consumed directly by tool binding (`parameters` on the function-schema dict :808-816).

### Decisive source
```python
# mcp_manager.py:793-800 + 821-827 — include is applied twice, and mismatches WARN loudly
for tool in tools:
    if include_set and tool.name not in include_set:
        continue
    ...
if include_set:
    actual_names = {tool.name for tool in tools}
    unmatched = include_set - actual_names
    if unmatched:
        logger.warning(f"MCP server '{name}': include list contains entries that don't match any tool: {unmatched}")
```
The two sites answer different threats: the list-time filter keeps the LLM-facing catalog clean; the registration-time check prevents a stale `include:` entry from silently becoming an invisible no-op — the operator sees exactly which configured names matched nothing.

**Flow:** connect → `list_tools()` under 15s timeout → store raw tool list (filtered) in `schemas[name]` → per included tool: flatten inputSchema, build function-dict, register maps → later `get_apis_for_application` re-projects these through `_convert_mcp_parameters_to_openapi_format` (:401-436) which reads the FLAT properties (enum values rendered into human-readable constraints `"must be one of: [...]"`).
**Invariant:** Flattening must NEVER lose a parameter it can't understand — degrade to `string` with an honest description instead of dropping (the model can still pass something). The flattener wraps everything in try/except returning the ORIGINAL schema: a malformed exotic schema must degrade to "unflattened" rather than kill the whole server connection. Prefixed hoisted keys (`parent_child`) change the arg name the model must emit — callers reading flattened schemas see ONLY flattened names.
**Probe:** direct tests `mcp_manager/tests/test_array_handling.py` (main vs v0 parser array handling :106/:163, enum-item arrays :261, nested arrays :310, constraint preservation :362); sanitizer/collision suite pins the surrounding registration loop (`test_dashed_tool_names.py`). Coverage caveat: the `$ref`-unresolvable→string fallback branch itself has no dedicated test.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_flatten_tool_parameters _flatten_schema_recursive _convert_mcp_parameters_to_openapi_format", limit: 10 });`

## Verdict
Adopt lossy-safe flattening (string-degrade, never drop), original-on-exception, and dual-site include filtering with unmatched-name warnings. Adapt prefix style to your naming rules. Omit array-item simplification if your models handle object arrays.
