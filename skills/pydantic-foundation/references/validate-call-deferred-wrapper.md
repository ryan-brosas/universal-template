<!-- capsule-v2 -->
# ValidateCallWrapper deferred build — when does a `@validate_call`-decorated function compile its schema, and what identity survives wrapping?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** How does a function wrapper validate args+kwargs as one value while preserving the original function's metadata and deferring schema build?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_validate_call.py:ValidateCallWrapper` (:50-141) + `update_wrapper_attributes` :29-47.
**Signature:** `ValidateCallWrapper(function: ValidateCallSupportedTypes, config: ConfigDict | None, validate_return: bool, parent_namespace: MappingNamespace | None)`; `__call__(*args, **kwargs) -> Any`.
**Data Shape:** slots hold `function`, `schema_type`, `module`, `qualname`, `ns_resolver`, `__pydantic_complete__`, `__pydantic_validator__`, `__return_pydantic_validator__`.

### Decisive source
```python
if isinstance(function, partial):
    self.schema_type = function.func          # unwrap partial for SCHEMA…
    self.module = function.func.__module__
else:
    self.schema_type = function
    self.module = function.__module__
self.qualname = extract_function_qualname(function)  # …but name it partial(<name>)
...
if not self.config_wrapper.defer_build:
    self._create_validators()
else:
    self.__pydantic_complete__ = False

def __call__(self, *args, **kwargs):
    if not self.__pydantic_complete__:
        self._create_validators()
    res = self.__pydantic_validator__.validate_python(pydantic_core.ArgsKwargs(args, kwargs))
    if self.__return_pydantic_validator__:
        return self.__return_pydantic_validator__(res)
    return res

# return validation of an async function awaits FIRST:
async def return_val_wrapper(aw):
    return validator.validate_python(await aw)
```

**Flow:** decoration captures (function, config, validate_return, parent namespace) → NsResolver seeded from `ns_for_function(schema_type)` → eager build unless `defer_build`, in which case first CALL builds → all positional/kw args validated as a single `ArgsKwargs` value against the generated parameters schema → optional return validation (awaited result for coroutines).
**Invariant:** the public wrapper is a NEW async-or-sync function chosen by the WRAPPED function's coroutine status, carrying functools.wraps metadata plus manually set `__name__/__qualname__` (`partial(...)` prefix) and `raw_function = wrapped`; lazy build is one-shot per call gate but re-checks until complete.
**Probe:** `tests/test_validate_call.py::test_wrap`/`test_func_type` :31-55 pin doc/name/module/qualname, `callable(foo_bar.raw_function)`, and `partial(f)` naming; `test_validate_call_defer_build` :1298-1311 pins lazy build incl. forward-ref return type.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "ValidateCallWrapper defer_build ArgsKwargs raw_function", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-value ArgsKwargs validation, partial unwrapping split (schema vs naming), and the complete-flag lazy-build gate; adapt error/title naming (`core_config(title=self.qualname)`); omit plugin-aware `create_schema_validator` indirection if your host has no validator plugins.
