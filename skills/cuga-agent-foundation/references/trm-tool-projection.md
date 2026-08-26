<!-- capsule-v2 -->
# TRM tool projection — why do dynamic tools get FAKE `path`/`method` fields and a synthetic success/failure response envelope?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your tool catalog is OpenAPI-shaped (path/method/parameters/response_schemas), but some tools come from a runtime service with no HTTP routes — how do you project them into the same shape without lying to the LLM?

## Shape-normalizing projection for non-OpenAPI sources
**Path/Symbol:** `src/cuga/backend/tools_env/registry/mcp_manager/mcp_manager.py` — fetch `_get_trm_tools` :492-505 (GET `{url}/api/v1/tools/` with auth header keyed BY AUTH TYPE, keep only configured `app_tools`, store under `f"{app}_{tool}"` key); projection `get_apis_for_application` TRM branch :578-600; converters `_convert_trm_parameters_to_openapi_format` :438-473 and `_convert_trm_response_schema` :475-490 (`{"success": schema, "failure": {"error": "string"}}`); execution detour `call_tool` :507-526 (TRM hit? → POST `LOCAL_TRM_URL/api/v1/runtime/tools/{id}/run?tool_type={binding_type}` with `{args, type, function}` payload → wrap `data.tool_output` in TextContent); MCP twin `_convert_mcp_parameters_to_openapi_format` :401-436 + MCP branch :629-668.
**Signature:** per tool: `{api_name: prefixed, app_name, secure: False, path: f"/{tool_name}", method: "POST", description, parameters: openapi-style list, response_schemas}`.
**Data Shape:** parameter entries carry `"constraints": ["must be one of: [a, b]"]` rendered FROM enum lists into plain strings (:430-432) — human-readable constraints instead of JSON-Schema enum blocks.

### Decisive source
```python
# mcp_manager.py:589-592 — synthetic route fields make the catalog UNIFORM
s_copy['secure'] = False
# Add missing fields for consistency with OpenAPI format
s_copy['path'] = f"/{tool_name}"
s_copy['method'] = "POST"
```
Downstream consumers (shortlister prompts, planners, formatters) were all written against the OpenAPI shape; projecting every source into that shape means exactly ONE rendering path. The fields are honestly fake — they exist for shape parity only and are never used for routing (TRM calls go through the id-based run endpoint).
```python
# mcp_manager.py:488-490 — same honesty about the response envelope
# TRM tools typically have a simple output schema
return {"success": trm_output_schema, "failure": {"error": "string"}}
```
**Flow:** load → fetch tool metadata per TRM app → filter by config.tools → project lazily when an app's APIs are requested → execute via runtime endpoint by tool ID. The MCP branch mirrors this: no-outputSchema tools get `{"success": {"type": "string"}, "failure": …, "_synthetic_placeholder": True}` (:654-664) so weak-schema detection downstream can tell "synthetic string placeholder" apart from "genuinely returns a bare string" — marker contract shared with prompt_utils (see capsule `weak-schema-sentinel.md`).
**Invariant:** Catalog consumers must never branch on tool SOURCE — if you add a fourth tool kind, project it into the canonical shape rather than adding branches at every consumer. Prefixed naming (`{app}_{tool}`) is the global uniqueness key across ALL sources (TRM/MCP/OpenAPI share one namespace).
**Probe:** coverage caveat — TRM fetch/projection has no direct test file upstream (requires a live TRM service); the OpenAPI-parameter converter it clones is pinned via parser tests. Verify by reading :492-526 and :578-600 before porting.
**Retrieve:** `await mcp.codebaseMemory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "_convert_trm_parameters_to_openapi_format _get_trm_tools trm_tools get_apis_for_application", limit: 10 });`

## Verdict
Adopt shape-normalizing projections (synthetic path/method/response-envelope marked as such), prefixed global tool namespace, and id-based execution detours. Adapt field names to your catalog schema. Omit if your tools are natively uniform.
