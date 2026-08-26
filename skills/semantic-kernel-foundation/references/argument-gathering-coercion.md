<!-- capsule-v2 -->
# Argument gathering & coercion — coerce only concrete single types; missing required raises, missing optional is omitted

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When tool arguments arrive as JSON-shaped values (dicts, strings), where do they get converted into the Python types the method declared — and what exactly happens when an argument is missing?

## Gather loop + `_parse_parameter` coercion ladder
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_from_method.py:gather_function_parameters` (170–192) with `._parse_parameter` (124–150).
**Signature:** `def _parse_parameter(self, value: Any, param_type: Any) -> Any`.
**Data Shape:** Coercion gate: run ONLY when `param.type_` is truthy, contains no comma (i.e., a single concrete type after the Optional/union ladder), and `type_object` is not `_empty`/`Any`. Ladder: pydantic (`model_validate`) → `list[X]` elementwise → dict→`cls(**value)` → plain callable ctor. Every failure re-raises as `FunctionExecutionException`.

### Decisive source
```python
if param.name in context.arguments:
    value = context.arguments[param.name]
    if (param.type_ and "," not in param.type_ and param.type_object
            and param.type_object is not inspect._empty and param.type_object is not Any):
        try:
            value = self._parse_parameter(value, param.type_object)
        except Exception as exc:
            raise FunctionExecutionException(
                f"Parameter {param.name} is expected to be parsed to {param.type_object} but is not.") from exc
    function_arguments[param.name] = value
    continue
if param.is_required:
    raise FunctionExecutionException(f"Parameter {param.name} is required but not provided in the arguments.")
logger.debug(f"Parameter {param.name} is not provided, using default value {param.default_value}")
```

**Flow:** Present argument → coerce if the gate passes, else pass through raw → absent REQUIRED parameter ⇒ FunctionExecutionException (propagates out of invoke) → absent OPTIONAL parameter ⇒ simply NOT included in kwargs, so the method's own Python default applies at call time.
**Invariant:** `KernelParameterMetadata.default_value` is schema documentation for the LLM/tool view — it is never injected into the call; optional-omission semantics come from Python itself. Unions/comma types skip coercion entirely rather than guessing a member.
**Probe:** `python/tests/unit/functions/test_kernel_function_from_method.py::test_required_param_not_supplied` (249–257) pins the raise; `test_service_execution_with_complex_object_from_str` (285–298) pins dict→pydantic coercion of `InputObject`; `_parse_parameter` unit tests (473–536) pin list-elementwise parsing, non-list TypeError wrap, invalid-dict/invalid-value wraps, and non-pydantic `cls(**value)` construction.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "gather_function_parameters is_required FunctionExecutionException parse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the coercion gate (single-concrete-type only) plus omit-optionals-so-Python-defaults-apply: together they avoid double-defaulting bugs where metadata defaults diverge from code defaults. Adapt the ladder ordering to your type system (e.g., add dataclass support before callable ctor). Omit per-parameter coercion entirely if your tools accept JSON natively — but then declare everything as untyped/Any so the gate stays consistent.
