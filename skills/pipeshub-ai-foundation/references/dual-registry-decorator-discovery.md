<!-- capsule-v2 -->
# Dual-registry decorator discovery — how do you auto-discover toolsets AND MCP server templates at startup without a hardcoded instance list drifting from the code?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What do the two registries (ToolsetRegistry for implemented tools, MCPRegistry for pure-metadata templates) actually store, how does registration fail, and why is one import-failure silent while duplicate type_ids are loud?

## Decorator stamps metadata; registry imports modules and reflects
**Path/Symbol:** `backend/python/app/agents/registry/toolset_registry.py:Toolset/register_toolset/_discover_tools_from_class/auto_discover_toolsets/get_all_registered_toolsets` (L19–660); `agents/mcp/mcp_server_decorator.py:mcp_server` (L20–47); `agents/mcp/registry.py:MCPRegistry.auto_discover_templates/get_template` (L25–49).
**Signature:** `@Toolset(name, app_group, supported_auth_types: str|list[str], description="", category, config=None, tools=None, internal=False, essential=False)` class decorator; `register_toolset(cls) -> bool`; `_discover_tools_from_class(cls) -> list[dict]`; `get_all_registered_toolsets(page=1, limit=20, search=None, include_tools=True) -> dict`.
**Data Shape:** Registry row = `{class, name, normalized_name (lowercased, spaces+underscores stripped), display_name, description, category, app_group/group, supported_auth_types[], config, tools[], icon_path, isInternal, essential}`. MCP side stores only `MCPServerTemplate` metadata under normalized `type_id` — no implementations; the live tool list is discovered from the RUNNING server.

### Decisive source
```python
# ToolsetRegistry._discover_tools_from_class — dual-era tool extraction over vars():
for attr_name in list(vars(toolset_class)):
    actual_func = getattr(attr, '__func__', attr)
    if hasattr(actual_func, '_tool_metadata'):            # legacy connector-style meta
        ... parameters via _convert_parameters_to_dict (args_schema.model_fields →
        Union unwraps first non-None arg; str/int/float/bool/list/dict mapping;
        unknown → 'string')
    elif hasattr(actual_func, AGENT_LOOP_TOOL_META_ATTR):  # agent_loop_lib @tool meta
        tool_name = agent_meta.path.rsplit("/", 1)[-1]     # LAST path segment IS the name
        tags → [{'key': t.key, 'value': t.value} dicts]
    # per-attr try/except continue — one bad method never kills registration

# register_toolset failure posture: missing metadata/name → logger.warning + False;
# ANY exception inside → logger.error(exc_info) + False. Registration NEVER raises.
#
# MCP decorator, by contrast:
if type_id in _MCP_SERVER_TEMPLATES:
    raise ValueError(f"Duplicate MCP server template type_id: {type_id}")   # LOUD
...
def get_template(self, type_id):
    if not type_id: return None                              # blank never KeyErrors
    return self._templates.get(normalize_mcp_type(type_id))  # lookup re-normalizes
```
Discovery asymmetry is deliberate: `MCPRegistry.auto_discover_templates()` pkgutil-imports every module under `app.agents.mcp.servers`, swallowing per-module import errors (log + continue) so one broken template file can't take down connectors-service startup — then snapshots `get_registered_templates()` ONCE and latches `_discovered = True`. `essential=True` on the decorator is the declarative single source of truth for lazy-disclosure pinning (`factory.py` reads it instead of a hardcoded pin list).

**Flow:** import-time decorators stamp `_toolset_metadata` / template objects onto classes → startup calls `auto_discover_*` which imports known action-module paths (toolsets: an explicit standard-paths list with commented-out disabled entries; MCP: pkgutil walk of the servers package) → per-class reflection extracts tools → rows stored under NORMALIZED keys → all lookups re-normalize (`get_template`, `get_toolset_metadata`) → frontend listing filters `isInternal`, paginates after sort-by-display-name, and searches displayName/description/appGroup case-insensitively.
**Invariant:** (1) Registration failures are boolean/logged, never raised — but duplicate MCP type_id raises at DECORATION time (import time), making a copy-pasted template impossible to ship silently. (2) Name normalization must be applied identically at write and every read; raw-name lookups miss. (3) `serialize=True` sanitization strips callables/type objects/dataclasses from configs before frontend exposure (`_sanitize_config`/`_sanitize_oauth_configs`); `serialize=False` keeps dataclass instances for internal callers. (4) One broken module or method degrades to log-and-skip — partial registries are preferable to failed boot. (5) Pagination/search happen AFTER internal filtering and sorting, so page boundaries are stable.
**Probe:** `tests/unit/agents/test_toolset_registry.py`: string_auth_type_normalized :28; empty_auth_types_raises :58; singleton :133; register_no_metadata_returns_false :138; normalize_toolset_name :175; optional_str→string :241; unknown_defaults_to_string :244; sanitize skips_callable :270 / preserves_oauth_configs_key :265 / dataclass_skipped :295; internal_toolsets_excluded :345; search_filter :362. `tests/unit/agents/mcp/test_registry.py`: duplicate_type_id_raises :42; auto_discover_templates_loads_builtin_servers :65; auto_discover_is_idempotent :109; get_template_empty_type_id_returns_none :127; auto_discover_skips_modules_that_fail_to_import :136.

## Get live surrounding code
**Retrieve:**
```bash
codebase-memory-mcp cli search_graph --project pipeshub-ai --query "ToolsetRegistry register_toolset _discover_tools_from_class MCPRegistry auto_discover_templates" --detail ids
```

## Verdict
Adopt the decorator-stamp + import-driven discovery shape, normalized-key storage with re-normalizing lookups, boolean-not-raise registration with loud duplicate-template detection, dual-era tool-meta extraction, and serialize-vs-internal split. Adapt the module-path lists and icon defaults to the host. Omit the specific product toolset roster and frontend API shapes.
