<!-- capsule-v2 -->
# Agent save/push packaging — what artifacts does `save()` emit, and how do requirements get discovered?

**Source:** smolagents Apache-2.0 `main@30bb1161`; Codebase Memory `ext-smolagents`. **Question:** What is the on-disk layout produced by `MultiStepAgent.save`/`Tool.save`, which fields are deliberately excluded from serialization, and where does the requirements list come from?

## Folder-of-code bundle
**Path/Symbol:** `src/smolagents/agents.py:save` (:892-968), `to_dict` exclusions (:970-1008), `push_to_hub` (:1160-1212); `tools.py:Tool.to_dict/:save/:_prepare_hub_files` (:292-514); `utils.py:instance_to_source/:ImportFinder/:get_source` (:268-427), gradio app template (:451-494).
**Signature:** `save(output_dir, relative_path=None)` → `__init__.py`s, `tools/{name}.py`, `managed_agents/{name}/…`, `prompts.yaml`, `agent.json`, `app.py`, `requirements.txt`; Hub push = tempdir save → upload_folder (repo_type="space", gradio SDK, tags ["smolagents","agent"]).
**Data Shape:** agent.json = to_dict() with tools reduced to NAME list and managed_agents to {name: ClassName}; prompts.yaml dumped with `default_style="|"` forcing block literals so multiline prompts survive round-trip.

### Decisive source
```python
# agents.py :976-979 — closures are honestly declared non-serializable:
# TODO: handle serializing step_callbacks and final_answer_checks
for attr in ["final_answer_checks", "step_callbacks"]:
    if getattr(self, attr, None):
        self.logger.log(f"This agent has {attr}: they will be ignored by this method.", LogLevel.INFO)
# tools.py :357 — requirements by AST import scan, stdlib-excluded, smolagents forced:
requirements = {el for el in get_imports(tool_code) if el not in sys.stdlib_module_names} | {"smolagents"}
```

**Flow:** save() walks the agent tree recursively (managed_agents get their own subfolders with dotted relative_path for import correctness), writes each tool via instance_to_source (class attrs minus dunders/_abc_impl/base-inherited values; methods re-indented under the class; wrapped functions unwrapped via __wrapped__), renders app.py from a Jinja template with camelcase filter for tool imports. Requirements come from scanning the GENERATED code's imports — not from introspecting the live environment — so a tool using lazy imports inside forward still gets its dependency listed only if imported at module scope of the emitted code.
**Invariant:** The bundle must be executable WITHOUT smolagents internals beyond the package itself: that's why prompts.yaml uses block-literal YAML (indentation-preserving), why tool code is regenerated source rather than pickles, and why callbacks are loudly dropped instead of silently lost.
**Probe:** `tests/test_utils.py::test_e2e_class_tool_save/:test_e2e_ipython_class_tool_save/:test_e2e_function_tool_save` (:213-380), `tests/test_agents.py::test_multiagents_save` (:2382+). Live: save a two-level agent tree → verify managed_agents/{n}/agent.json + dotted imports.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-smolagents", query: "instance_to_source ImportFinder make_init_file push_to_hub", limit: 10, fields: ["signature","name","file"] });
```

## Verdict
Adopt code-regenerating bundles with AST-derived requirements. Adapt the Space-specific push metadata. Never serialize callables you can't re-source — drop them loudly like step_callbacks.
