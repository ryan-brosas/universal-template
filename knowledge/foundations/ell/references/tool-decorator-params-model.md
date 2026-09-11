<!-- capsule-v2 -->
# tool decorator params model — how do I synthesize a typed JSON schema for a tool from its signature?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I turn a plain typed Python function into a vendor-ready tool schema without asking the author to declare a params model?

## signature → create_model
**Path/Symbol:** `src/ell/lmp/tool.py:tool` (:18-138; model synthesis :89-121).
**Signature:** `tool(*, exempt_from_tracking: bool = False, **tool_kwargs)` returning decorator `(fn) -> InvocableTool`.
**Data Shape:** `wrapper.__ell_params_model__ = create_model(fn.__name__, **fields)` where fields map param name → `(annotation, FieldInfo|default|Field(...))`; `get_params_model()` helper attached for late access.

### Decisive source
```python
# tool.py:93-118
for param_name, param in sig.parameters.items():
    # Skip *args and **kwargs
    if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
        continue

    if param.annotation == inspect.Parameter.empty:
        raise ValueError(f"Parameter {param_name} has no type annotation, and cannot be converted into a tool schema for OpenAI and other provisders. Should OpenAI produce a string or an integer, etc, for this parameter?")
    annotation = param.annotation

    # Determine the default value
    default = param.default

    # Check if the parameter has a Field with description
    if isinstance(param.default, FieldInfo):
        field = param.default
        fields[param_name] = (annotation, field)
    elif param.default != inspect.Parameter.empty:
        fields[param_name] = (annotation, param.default)
    else:
        fields[param_name] = (annotation, Field(...))

model_name = f"{fn.__name__}"
ParamsModel = create_model(model_name, **fields)
wrapper.__ell_params_model__ = ParamsModel
```

**Flow:** at decoration time (not call time) the signature is walked once; VAR_POSITIONAL/VAR_KEYWORD skipped; untyped params raise immediately with an actionable message; `FieldInfo` defaults (with descriptions) are preserved as-is so LLM-visible field docs survive. The model's `model_json_schema()` is what providers embed (`openai.py:49`, `anthropic.py:61` as `input_schema`, `bedrock.py:56` under `json=`).
**Invariant:** fail-closed on missing annotations — silently emitting `Any` would produce unusable schemas. The docstring is the tool description (`__doc__` read directly by each provider translator); a porter that drops docstring propagation loses all tool documentation.
**Probe:** `tests/test_tools.py:test_tool_json_dumping_behavior` (:7-52) executes decorated tools through the wrapper envelope; schema emission pinned by `tests/test_openai_provider.py:test_translate_to_provider_with_tools` (:135-163, exact JSON schema dict incl. `"title": "MyModel"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "get client for model fallback", limit: 5, fields: ["signature", "name", "file"] });
// adjacent seam resolution works; for this capsule use:
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "tool result content block", limit: 5, fields: ["signature", "name", "file"] });
// rank-1 test-side anchor: tests/test_message_type.test_content_block_coerce_tool_result @ tests/test_message_type.py:34-39
```

## Verdict
Adopt signature-driven pydantic synthesis and the raise-on-untyped stance. Adapt the skip-list (positional-only params need handling on 3.8+ grammars you target). Omit `**tool_kwargs` pass-through unless your registry consumes extra metadata — ell itself only stashes it on `__ell_tool_kwargs__`.
