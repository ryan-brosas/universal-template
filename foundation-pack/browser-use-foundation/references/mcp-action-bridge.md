<!-- capsule-v2 -->
# MCP tool → action registry bridge — how do external MCP tools become first-class agent actions?

**Source:** browser-use MIT `main@3c989dc`; Codebase Memory `browser-use`. **Question:** how are MCP JSON Schemas converted to pydantic param models and registered onto an existing action registry at runtime?

## Connected graph-selected seam
**Path/Symbol:** `browser_use/mcp/controller.py` whole (264L) — `MCPToolWrapper` (:23), `connect` (:43), `_register_tool_as_action` (:80), `mcp_action_wrapper` (:113), `_json_schema_to_python_type` (:228), `register_mcp_tools` (:250).
**Signature:** `_register_tool_as_action(tool_name: str, tool: Tool)`; `_json_schema_to_python_type(schema: dict) -> Any`.

### Decisive source
```python
for param_name, param_schema in properties.items():
    param_type = self._json_schema_to_python_type(param_schema)
    if param_name in required: default = ...          # Ellipsis = required field
    else: default = param_schema.get('default', None)
    field_kwargs = {'description': param_schema['description']} if 'description' in param_schema else {}
    param_fields[param_name] = (param_type, Field(default, **field_kwargs))
param_model = create_model(f'{tool_name}_Params', **param_fields) if param_fields else None

async def mcp_action_wrapper(**kwargs):
    special_params = {'page','browser_session','context','page_extraction_llm','file_system',
                      'available_file_paths','has_sensitive_data','browser','browser_context'}
    tool_params = {k: v for k, v in kwargs.items() if k not in special_params}
    result = await self.session.call_tool(tool_name, tool_params)
    # list[TextContent] -> '\n'.join(texts); str() fallbacks everywhere
    return ActionResult(extracted_content=extracted_content)

mcp_action_wrapper.__name__ = tool_name                    # debuggable registry entries
decorated_wrapper = self.registry.action(description=tool.description or f'MCP tool: {tool_name}',
                                        param_model=param_model, domains=domains)(mcp_action_wrapper)
```

**Flow:** stdio_client + ClientSession context managers spawn the server process → `initialize()` + `list_tools()` discover the surface → each tool's JSON Schema properties become a dynamically-created pydantic model (`create_model`) with required=Ellipsis convention → wrapper closures strip registry-injected special params before calling `session.call_tool` → results flattened to ActionResult.extracted_content; errors become extracted+error dual-filled results, never raises.
**Invariant:** JSON-schema type mapping is intentionally lossy (object→dict, array→list, nullable→`| None`); the special-param filter MUST stay in sync with the registry's injection set or injected dependencies leak to the remote tool; session lifecycle relies on the outer async-with blocks (disconnect just releases the reference).
**Probe:** `tests/ci/test_mcp_tool_annotations.py` (annotation surface); connect/disconnect lifecycle covered by source citation only (coverage caveat).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "browser-use", query: "MCPToolWrapper _register_tool_as_action create_model call_tool inputSchema", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt schema→create_model conversion + closure-based registration + special-param stripping; adapt result flattening to your content types; omit the legacy `browser_`-prefix domain detection if unused.
