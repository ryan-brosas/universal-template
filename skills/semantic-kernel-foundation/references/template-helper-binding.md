<!-- capsule-v2 -->
# Template helper binding — how do kernel functions become callable helpers inside Jinja2/Handlebars templates, and how do async tools work under a synchronous engine?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** When a non-Kernel template calls a kernel function, what callable is it actually given, how are its arguments assembled, and how does an async tool complete inside a blocking template engine?

## Sync/async helper split
**Path/Symbol:** `python/semantic_kernel/prompt_template/utils/template_function_helpers.py:create_template_helper_from_function` (26–67), `_create_sync_template_helper_from_function` (70–113), `_create_async_template_helper_from_function` (116–141).
**Signature:** `def create_template_helper_from_function(function: KernelFunction, kernel: Kernel, base_arguments: KernelArguments, template_format: TEMPLATE_FORMAT_TYPES, allow_dangerously_set_content: bool = False, enable_async: bool = False) -> Callable[..., Any]`.
**Data Shape:** returns a plain closure. The async variant exists ONLY for Jinja2 (`enable_async=True` with any other format raises ValueError at creation). The sync variant works for both engines.

### Decisive source
```python
if not getattr(asyncio, "_nest_patched", False):
    nest_asyncio.apply()

def func(*args, **kwargs):
    arguments = KernelArguments()
    if base_arguments and base_arguments.execution_settings:
        arguments.execution_settings = base_arguments.execution_settings
    arguments.update(base_arguments)
    arguments.update(kwargs)                       # kwargs WIN over base arguments
    if len(args) > 0 and template_format == HANDLEBARS_TEMPLATE_FORMAT_NAME:
        this = args[0]                             # Handlebars `this` context, stripped
        actual_args = args[1:]
    else:
        this, actual_args = None, args
    result = asyncio.run(function.invoke(kernel=kernel, arguments=arguments))
    if allow_dangerously_set_content:
        return result
    return escape(str(result))                    # HTML-escaped by default in BOTH engines
```

**Flow:** dispatch on `enable_async`; the sync helper patches the running event loop ONCE per process (`nest_asyncio.apply()`, guarded by the private `asyncio._nest_patched` attribute) and then bridges each call with `asyncio.run(function.invoke(...))` — the calling thread BLOCKS until the tool completes, which is what makes async tools usable from a synchronous engine like pybars. The argument bag is a FRESH KernelArguments per call: execution settings carried over from the base bag, base arguments applied first, template-supplied kwargs last (kwargs win on name collision). Handlebars passes its `this` context as `args[0]`; it is stripped only when the format is handlebars (Jinja2 positional args are all real arguments). The result is returned raw only when `allow_dangerously_set_content` is set; otherwise it is `escape(str(result))` — HTML-escaped and stringified by default in both engines.
**Invariant:** one nest_asyncio patch per process (the guard reads a CPython-internal attribute — a porting hazard); kwargs always beat base arguments; escaping is the DEFAULT, trust is the opt-in; the async path never touches nest_asyncio because it awaits inside the live loop.
**Probe:** `python/tests/unit/prompt_template/test_template_helper.py::test_create_helpers` (12–37, `int(str(result(x=1))) == 2` proves the str-escape round trip); `::test_create_helpers_fail` (40–53, parametrized matrix: `handlebars + enable_async=True` → ValueError; `semantic-kernel` → ValueError in both modes; jinja2 works in both modes).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "create_template_helper_from_function nest_asyncio asyncio.run escape allow_dangerously_set_content", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the fresh-bag-per-call argument assembly with kwargs-wins ordering, the escape-by-default result contract, and the format-gated async split. Adapt the nest_asyncio bridge to your host's concurrency model (it is a CPython-specific hack keyed on a private attribute) and the `this`-context stripping to your engine's calling convention. Omit nothing from the creation-time ValueError for unsupported format/async combinations — failing at helper construction beats failing mid-render.
