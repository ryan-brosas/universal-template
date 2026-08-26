<!-- capsule-v2 -->
# function_to_json — How does a plain Python callable become an OpenAI tools-schema entry, and where does it silently degrade?

**Source:** OpenAI Swarm MIT `main@6af0b4caf37dca4526dfd98e9fbd8ce36e7eeb22`; Codebase Memory `ext-openai-swarm`. **Question:** What schema does a porter get for untyped/typed params, defaults, and docstrings — and which mistakes produce wrong-but-accepted schemas?

## inspect-based schema with string fallback
**Path/Symbol:** `swarm/util.py:function_to_json` (31-87).
**Signature:** `function_to_json(func) -> dict`.
**Data Shape:** Returns the OpenAI tool envelope `{"type": "function", "function": {"name", "description", "parameters": {"type": "object", "properties", "required"}}}`.

### Decisive source
```python
type_map = {
    str: "string", int: "integer", float: "number",
    bool: "boolean", list: "array", dict: "object",
    type(None): "null",
}
...
for param in signature.parameters.values():
    try:
        param_type = type_map.get(param.annotation, "string")
    except KeyError as e:
        raise KeyError(...)
    parameters[param.name] = {"type": param_type}

required = [
    param.name
    for param in signature.parameters.values()
    if param.default == inspect._empty
]
```

**Flow:** `inspect.signature` (ValueError → re-raised with the function name) → per param: annotation looked up in the 7-entry map, anything else (including `Optional[str]`, `Literal`, pydantic models) degrades to `"string"` → required = params whose default is `inspect._empty`.
**Invariant:** Untyped params become `"string"` SILENTLY (`dict.get(..., "string")`) — a porter who expects validation gets none. The `except KeyError` guard is dead code: `.get` never raises. Docstring becomes the function description verbatim (`func.__doc__ or ""`). Defaults drive `required` only — default VALUES are never advertised to the model.
**Probe:** `tests/test_util.py:test_basic_function` + `test_complex_function` (exact-dict assertions pinning untyped→string, int/float/bool mapping, docstring passthrough, required-from-defaults).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-openai-swarm", query: "function_to_json signature", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt as the minimal viable schema generator (~40 lines, zero deps). Adapt: swap the silent string-fallback for a hard error or a richer mapper (typing.get_type_hints / pydantic) when your host needs faithful schemas — smolagents and pi both harden this exact seam. Omit the dead KeyError branch; keep the ValueError wrap.
