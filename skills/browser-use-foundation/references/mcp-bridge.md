<!-- capsule-v2 -->
# MCP bridge — JSON-Schema tools compiled into the native action registry

**Source:** browser-use MIT `<branch>@<commit>`; Codebase Memory `browser-use`. **Question:** how do external MCP tools become first-class agent actions (typed params, registry-registered, schema-enforced) instead of a parallel tool path?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/mcp/client.py` (556 lines): `MCPClient` (:47) — `connect` (:80, stdio + HTTP transports), `register_to_tools` (:212), `_register_tool_as_action` (:248-360), `_json_schema_to_python_type`, `_format_mcp_result` (:419); also exposes browser-use AS an MCP server (`mcp/server.py`, `manifest.json`). Registry contract in `tools/registry/service.py`.
**Signature:** `register_to_tools(registry)` — for each MCP tool: parse its JSON Schema → synthesize a pydantic param model (`create_model(..., extra='forbid')`) → wrap an async closure calling the MCP client → `registry.action(...)` it under a sanitized name.
**Data Shape:** MCP `inputSchema {properties, required}` → pydantic fields (required → `...`, optional → `type | None` with schema default); results normalized to `ActionResult` strings via `_format_mcp_result`.

### Decisive source
```ts
for param_name, param_schema in properties.items():
    param_type = self._json_schema_to_python_type(param_schema, f'{action_name}_{param_name}')
    if param_name in required:
        default = ...                                  # required field
    else:
        param_type = param_type | None                 # optional
        default = param_schema.get('default', None)
    param_fields[param_name] = (param_type, Field(default, description=...))
class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(extra='forbid', validate_by_name=True, validate_by_alias=True)
param_model = create_model(f'{action_name}_Params', __base__=ConfiguredBaseModel, **param_fields)
# then: async mcp_action_wrapper(params) -> ActionResult  registered via registry.action()
```

**Flow:** connect over stdio/HTTP → list tools → each becomes a native action: JSON Schema translated to pydantic types (descriptions preserved), wrapper closure calls the MCP server and stringifies the result into `ActionResult` → from then on the LLM sees MCP tools indistinguishably from built-ins (same union schema, same domain filtering, same secret substitution). The reverse direction also exists: browser-use publishes itself as an MCP server so other agents can drive it.
**Invariant:** external tools enter through ONE gate (the registry) — no second execution path; generated models forbid extra fields; transport and schema quirks stay inside the client.
**Probe:** `tests/` mcp tests (stdio connect; schema→model conversion incl. nested types; action callable end-to-end; result formatting).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-use", query: "MCPClient register_to_tools _register_tool_as_action json_schema inputSchema ActionResult", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt compiling foreign tool schemas into your native registry (one execution path for everything); adapt type mapping to host's schema dialect.
