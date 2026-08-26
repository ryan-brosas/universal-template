<!-- capsule-v2 -->
# @tool decorator source capture — how does a plain function become a Tool that can regenerate its own code?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What does the `tool()` decorator build at decoration time so the resulting SimpleTool can be serialized back to a standalone class file (Hub push, remote executor install)?

## AST-sourced forward synthesis
**Path/Symbol:** `src/smolagents/tools.py:tool` (:1061-1168); schema from `_function_type_hints_utils.get_json_schema`; consumers `Tool.to_dict` SimpleTool branch (:295-341), `get_tools_definition_code` (:1335-1358).
**Signature:** `tool(tool_function) -> SimpleTool` — requires full type hints, docstring with `Args:` block, and return hint.
**Data Shape:** Produces class attrs (name/description/inputs/output_type, optional output_schema), a staticmethod forward bound to a wrapper of the original function with a SYNTHETIC signature (`self` prepended via `sig.replace`), plus two `__source__` attributes: class-level and forward-level text.

### Decisive source
```python
# :1112-1145 — the source pipeline: dedent → AST locate → strip decorators → re-indent as method
tool_source = textwrap.dedent(inspect.getsource(tool_function))
tree = ast.parse(tool_source)
func_node = next((node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)), None)
...
body_start = func_node.body[0].lineno - 1        # AST lineno starts at 1
tool_source_body = "\n".join(lines[body_start:])
forward_method_source = f"def forward{new_sig}:\n{tool_source_body}"   # new_sig has self FIRST
```

**Flow:** Decoration: JSON schema from type hints/docstring; missing return hint raises unless there are zero parameters (then `{"type":"null"}`); multiple @tool decorators raise; NON-tool decorators warn (issue #1626 — they won't survive serialization). The body slice starts at the first statement (docstring included) so decorator lines are dropped but the function's logic is byte-preserved. Serialization: `to_dict()` re-extracts forward source, renames the function to "forward", injects self if missing, embeds into a template class, then scans imports for requirements. Remote install (`get_tools_definition_code`) emits BASE_BUILTIN_MODULES imports + a minimal Tool shim + each tool's code so sandboxes can instantiate tools without smolagents.
**Invariant:** `inspect.getsource` availability is a hard dependency at DECORATION time (REPL-defined functions fail here, by design). The synthetic signature must keep parameter ORDER after inserting self, or positional calls shift. Decorators other than @tool are silently lost in the serialized copy — hence the loud warning.
**Probe:** `tests/test_function_type_hints_utils.py::TestGetJsonSchema*` (:241-298), `tests/test_tools.py` SimpleTool round-trips + `tests/test_utils.py::test_e2e_function_tool_save` (:324-380). Live: decorate a real-file function, `to_dict()["code"]`, exec in fresh module with only Tool/typing injected, call revived.forward → identical result.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "SimpleTool tool decorator __source__ forward_method_source", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt AST-based source capture when tools must be portable artifacts. Adapt requirement scanning. Omit the decorator entirely if you accept class-subclass authoring only — but then remote executors lose the lightweight path.
