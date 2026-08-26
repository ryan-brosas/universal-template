<!-- capsule-v2 -->
# Kernel-function decorator contract — eager metadata extraction at decoration time

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When should tool metadata be extracted from a Python callable — lazily at registration, or eagerly at import — and what exactly does the marker contract have to store?

## Dual-mode decorator writing six dunder attributes
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_decorator.py:kernel_function` (lines 13–84).
**Signature:** `def kernel_function(func: Callable[..., object] | None = None, name: str | None = None, description: str | None = None) -> Callable[..., Any]`.
**Data Shape:** Works bare (`@kernel_function`) or parameterized (`@kernel_function(name=..., description=...)`) via the `func is None` branch. Attributes written onto the function object: `__kernel_function__`, `__kernel_function_description__` (falls back to docstring), `__kernel_function_name__` (falls back to `__name__`, else `"unknown"`), `__kernel_function_streaming__`, `__kernel_function_parameters__` (list of dicts), plus four `__kernel_function_return_*` attrs.

### Decisive source
```python
def decorator(func):
    setattr(func, "__kernel_function__", True)
    setattr(func, "__kernel_function_description__", description or func.__doc__)
    setattr(func, "__kernel_function_name__", name or getattr(func, "__name__", "unknown"))
    setattr(func, "__kernel_function_streaming__", isasyncgenfunction(func) or isgeneratorfunction(func))
    func_sig = signature(func, eval_str=True)
    annotations = _process_signature(func_sig)
    setattr(func, "__kernel_function_parameters__", annotations)
    return_annotation = (
        _parse_parameter("return", func_sig.return_annotation, None) if func_sig.return_annotation else {}
    )
    setattr(func, "__kernel_function_return_type__", return_annotation.get("type_", "None"))
```

**Flow:** Decorate → set marker/description/name → detect streaming ONCE from the function kind (async/sync generator ⇒ streaming) → parse signature eagerly with `eval_str=True` → store parameter dicts and return-annotation dict. No return annotation ⇒ return type `"None"`, empty description, not required.
**Invariant:** Metadata parsing happens at import/decoration time, so a malformed annotation fails immediately at class-definition time — never at first invocation. The streaming flag is frozen here; later wrappers trust it instead of re-inspecting.
**Probe:** `python/tests/unit/functions/test_kernel_function_decorators.py::test_kernel_function_return_type_streaming` (179–185) pins that a generator-returning method gets `__kernel_function_streaming__ == True` while plain methods stay False; `test_init_method_is_not_kernel_function` in test_kernel_function_from_method.py (148–153) pins that binding without the marker raises `FunctionInitializationError`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "kernel_function decorator __kernel_function_name__", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt eager at-decoration metadata extraction + marker attributes for any plugin-tool registry: it turns signature errors into import-time failures and makes discovery a cheap `hasattr` scan (see `KernelPlugin.from_object`). Adapt attribute names/shape to your host; you can defer parsing lazily only if you keep an explicit "unparsed" state. Omit the docstring fallback if your tools always carry explicit descriptions.
