<!-- capsule-v2 -->
# Optional/Union type parsing — single non-None member unwraps, unions stay comma strings

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How do you turn Python annotations like `str | None`, `Annotated[str | int | None, "desc"]`, or `list[str]` into parameter metadata with correct requiredness and a display type?

## Recursive `_parse_parameter` + Optional unwrap ladder
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_decorator.py:_get_underlying_type` (98–112), `._parse_parameter` (135–193), `._process_signature` (115–132).
**Signature:** `def _get_underlying_type(annotation: Any) -> Any` / `def _parse_parameter(name: str, param: Any, default: Any) -> dict[str, Any]`.
**Data Shape:** Produces dicts `{name, description?, default_value?, is_required, type_, type_object?, include_in_function_choices?}`. Requiredness: explicit default ⇒ False; a `NoneType` union member ⇒ False + `default_value=None`; otherwise True.

### Decisive source
```python
def _get_non_none_type(args):
    non_none_types = [arg for arg in args if arg is not type(None)]
    if len(non_none_types) == 1:
        return non_none_types[0]
    return None          # >1 non-None member: keep the Union
...
for arg in param.__args__:
    if arg == NoneType:
        ret["is_required"] = False
        if "default_value" not in ret:
            ret["default_value"] = None
        continue
    ...
if ret.get("type_") in ["list", "dict"]:
    ret["type_"] = f"{ret['type_']}[{', '.join([arg['type_'] for arg in args])}]"
elif len(args) > 1:
    ret["type_"] = ", ".join([arg["type_"] for arg in args])
...
if not ret.get("include_in_function_choices", True):
    ret["is_required"] = False
```

**Flow:** Annotated metadata first (string ⇒ description; dict ⇒ merged keys) → recurse into `__origin__`/`__args__` → drop NoneType members flipping required off → compose generic strings (`list[str]`, `dict[str, str]`) or comma-joined unions (`"str, int"`) → finally, annotation-level `include_in_function_choices=False` forces the parameter out of requiredness (it becomes an injected/internal param).
**Invariant:** Only a SINGLE non-None union member is unwrapped to that concrete type (and its `type_object`); two or more members keep the union as a comma-separated string and remain REQUIRED. Downstream coercion relies on this: it only coerces when `"," not in param.type_`.
**Probe:** `python/tests/unit/functions/test_kernel_function_decorators.py::test_annotation_parsing` (248–282) pins 13 cases exactly: `("opt_str", str|None, ..., "str", False)`, `("anno_opt_str_int", Annotated[str|int|None,"test"], ..., "str, int", False)`, `("list_str_opt", list[str]|None, ..., "list[str]", False)`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "_get_underlying_type _parse_parameter annotation", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single-non-None unwrap rule and the comma-union convention verbatim — they decide which parameters appear in LLM tool schemas and which get runtime coercion. Adapt the string composition (`list[str]` vs JSON-schema style) to your tool-view format. Omit the ForwardRef/string-annotation branches only if you always call `signature(eval_str=True)` first.
