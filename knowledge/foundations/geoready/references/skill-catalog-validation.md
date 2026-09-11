<!-- capsule-v2 -->
# Internal skill catalog — YAML specs with AST-based MCP-tool cross-validation

**Source:** GeoReady (Geo Optimizer) MIT `main@a7165be2`; Codebase Memory `ext-aeo-geo-optimizer-skill`. **Question:** How do you ship validated prompt-skills inside a package whose workflow steps provably reference real engine surfaces?

## loader (path-confined) + validator (closed vocabularies + static tool discovery)
**Path/Symbol:** `src/geo_optimizer/skills/loader.py:load_skill` (33–96), `load_catalog` (99–120); `src/geo_optimizer/skills/validator.py:discover_mcp_tool_names` (66–90), `validate_skill` (127+).
**Signature:** `load_skill(skill_dir) -> SkillSpec`; `validate_catalog() -> dict[str, list[str]]`.
**Data Shape:** `skill.yaml` → `SkillSpec(schema_version=1, skill_id, kind ∈ {analysis, orchestrator, repair}, when_to_use[], required_inputs[], expected_outputs[], engine_surfaces[] as prefix:target, workflow[SkillStepSpec], guardrails[], prompt_text)`; catalog folders skipped when `_`-prefixed unless `include_templates`.

### Decisive source
```python
# validator: extract MCP tool names WITHOUT importing the module — the `mcp`
# package is an optional dependency, and this must work in site-packages too
server_resource = _resource_path("geo_optimizer.mcp", "server.py")
module = ast.parse(server_resource.read_text(encoding="utf-8"))
for node in module.body:
    if not isinstance(node, ast.FunctionDef): continue
    for decorator in node.decorator_list:
        if (isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and decorator.func.value.id == "mcp" and decorator.func.attr == "tool"):
            tool_names.add(node.name)

# loader: prompt file cannot escape its skill folder (path-traversal gate)
prompt_path = (skill_dir / prompt_file).resolve()
if not str(prompt_path).startswith(str(skill_dir.resolve()) + os.sep):
    raise ValueError(f"prompt_file escapes skill directory: {prompt_file}")
```

**Flow:** every spec must declare ≥1 surface per list field; surfaces validate against closed sets — `python_api:` names must appear in `geo_optimizer.__all__`, `mcp:` against AST-discovered tools, `plugin_hook:` limited to `geo_optimizer.checks`, `doc:` resolved through importlib.resources to the PACKAGED docs copy; prompts require five exact headings (`## Mission / Required Inputs / Execution Protocol / Output Contract / Guardrails`); workflow step ids unique + snake_case, and each step's `uses` ⊆ declared surfaces.
**Invariant:** Validation runs WITHOUT importing the MCP server (AST over the packaged file) so the dependency stays optional while the contract stays enforceable; folder-name == skill_id keeps catalog identity filesystem-anchored. A porter who imports server.py here turns a soft optional dep into a hard failure.
**Probe:** `tests/test_skill_system.py::test_catalog_validates_clean` (+ negative suites for bad surfaces; `PYTHONPATH=src pytest tests/test_skill_system.py -q` green at pin).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-aeo-geo-optimizer-skill", query: "skill catalog validator surfaces", limit: 5, fields: ["signature","name","file"] });
```

## Verdict
Adopt spec-file skills with static cross-validation of declared capabilities; adapt heading requirements/surface prefixes; omit i18n doc mirrors if you don't localize.
