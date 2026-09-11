<!-- capsule-v2 -->
# Toolset abstraction & connector builder — how does a class of @tool methods become a registered, grouped, lazy-disclosable toolset?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How do you turn a connector instance (Jira/Slack/...) into agent tools ONCE per class but bind them FRESH per authenticated instance — and which registry API must registration use?

## Class-keyed reflection cache + per-instance binding + register_tool/register_toolset (NOT the strict object variant)
**Path/Symbol:** `backend/python/app/agent_loop_lib/tools/toolset.py:Toolset/_tool_attrs_for_class/_TOOL_ATTR_CACHE/ToolsetBuilder` (L56–245).
**Signature:** `_tool_attrs_for_class(cls) -> list[(attr_name, ToolMeta)]`; `ToolsetBuilder(instance, *, name, description, path_prefix, tags=None)`; `register_into(registry)`; Toolset ABC properties `name/description/path_prefix` + default `tags`/`parent` + abstract `tools`.
**Data Shape:** `_TOOL_ATTR_CACHE: dict[type, list[(str, ToolMeta)]]` is process-global keyed by CLASS; instances only re-bind. Tag merge order in `list_tools()`: toolset tags FIRST then tool tags (both kept as-is on duplicate keys).

### Decisive source
```python
# Reflection looked up via the CLASS, not an instance:
"""Looked up via the CLASS rather than an instance so a @property on the
connector class returns the descriptor itself (never invoking the getter)
instead of evaluating it against whichever instance happens to trigger the
first cache miss."""
_TOOL_ATTR_CACHE: dict[type, list[tuple[str, ToolMeta]]] = {}
# ...fixed at import time and never changes for the life of the process,
# so the dir() scan below only needs to run once per class no matter how
# many per-request instances (each wrapping a different, freshly
# authenticated client) get built from it afterward.

def register_into(self, registry):
    """Uses register_tool + register_toolset rather than the stricter
    register_toolset_object — the latter validates tool.path ==
    f"{path_prefix}/{tool.name}", which doesn't hold for connector tools
    where tool.name is `app__method` (globally unique for LLM addressing)
    while the path uses the short method name."""
```

**Flow:** first construction of a connector class runs ONE dir() scan collecting @tool-decorated attrs → every later instance skips reflection and binds fresh BoundMethodTools onto its own client → path/prefix mismatch logs a warning but still includes the tool (declared path is authoritative) → register_into registers each tool with toolset-level extra_tags, then creates the named group powering list_toolsets/fetch_tools disclosure.
**Invariant:** (1) Cache is keyed by class and NEVER invalidated — safe only because @tool decoration is fixed at import time; adding runtime-mutable tool surfaces breaks this. (2) Instance state (auth client) must never leak into the cached metadata — binding happens per instance. (3) Connector registration MUST bypass register_toolset_object's path==prefix/name equality check because LLM-facing names (`app__method`) intentionally differ from path segments; using the strict variant here orphans every connector tool. (4) Categorization rides tags, not paths (see middleware-path-tag-routing); `parent` groups hierarchies for overview rendering.
**Probe:** `tests/unit/agent_loop_lib/tools/test_toolset_builder_cache.py` — :65 caches-per-class, :71 finds every decorated method, :76 independent entries per class, :87 two instances correctly bound (cache hit ≠ shared bound tools), :108/:113 cache-hit correctness.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ToolsetBuilder _tool_attrs_for_class _TOOL_ATTR_CACHE register_into BoundMethodTool", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt class-keyed import-time reflection caching + per-instance binding + lenient registration when exposing OO connectors as tool surfaces. Adapt naming convention (`app__method`) to host. Omit nothing portable. No coverage caveat — cache/binding behavior directly pinned.
