<!-- capsule-v2 -->
# Markdown→FastMCP flow export — how does a saved conversation turn into an executable MCP tool server without breaking the old one?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** How are ```python blocks AST-harvested into @mcp.tool functions and merged idempotently into an existing server file?

## AST harvest + create/update duality with validate-before-write
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/save_reuse/save_reuse_agent/utils/export_mcp.py:process_text_file` (:211-253), `extract_imports_and_functions_from_code` (:24-65), `generate_or_update_server` (:109-208), `parse_existing_server` (:68-96).
**Signature:** `process_text_file(input_file=None, output_file=None, mode='auto', input_text=None) -> bool`; `generate_or_update_server(all_functions_data, all_imports, output_file, mode) -> bool`.
**Data Shape:** functions `[{'name': str, 'source': str}]` reconstructed line-exact via `node.lineno/end_lineno`; imports `[{'source': str}]`; existing-server scan collects imports plus ONLY functions decorated `@mcp.tool` (Attribute value.id=='mcp', attr=='tool').

### Decisive source
```python
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                all_found_functions.append(node.name)
                if node.name == "call_api":
                    skipped_functions.append(node.name)
                    continue                      # reserved name never re-exported
                func_lines = code_lines[node.lineno - 1 : node.end_lineno]
                func_source = '\n'.join(func_lines)
```
and the update-mode guard:
```python
        if not validate_python_code(updated_content):
            logger.error("Critical Error: The updated code is not valid Python. Aborting update to prevent corruption.")
            return False
        output_file.write_text(updated_content, encoding='utf-8')
```

**Flow:** extract fenced python blocks → AST-parse each (SyntaxError → empty lists, logged) → collect top-level functions (skipping the RESERVED `call_api` name) + imports → mode auto = update iff file exists → CREATE writes preamble (`get_premable(is_local=settings.features.local_sandbox)`), `FastMCP("Demo 🚀")`, deduped imports (fastmcp import pre-seeded), SSE runner on `settings.server_ports.saved_flows`; UPDATE diffs against parsed existing file, inserts new imports after the LAST import line and functions BEFORE `if __name__ == "__main__":` (adjusting the marker offset by added-import newline count), no-op returns True when nothing new.
**Invariant:** Validate-before-write on EVERY path — a syntax-erroring merge aborts leaving the previous server intact. Idempotency: re-saving identical flows adds nothing. Line-exact reconstruction (never ast.unparse) preserves decorators/comments the model wrote. Porters who forget the `main_block_line += imports_to_add.count('\n') + 2` adjustment insert functions INSIDE the import block.
**Probe:** Recorded upstream gap (no dedicated test). Deterministic probe: `cd /tmp && python3 - <<'EOF'
import ast,sys
src=open('$REFERENCE_ROOT/agents/cuga-agent/src/cuga/backend/cuga_graph/nodes/save_reuse/save_reuse_agent/utils/export_mcp.py').read()
tree=ast.parse(src)
names={n.name for n in tree.body if isinstance(n,(ast.FunctionDef,))}
assert {'process_text_file','generate_or_update_server','parse_existing_server','validate_python_code'} <= names
EOF`

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "process_text_file generate_or_update_server parse_existing_server FastMCP", limit: 6, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt AST-based function/import harvesting with line-exact source preservation, the reserved-name skip, insertion-point bookkeeping, and validate-before-write. Adapt the server preamble/port config. Omit the CLI main(); wire `process_text_file` directly like ReuseAgent does.
