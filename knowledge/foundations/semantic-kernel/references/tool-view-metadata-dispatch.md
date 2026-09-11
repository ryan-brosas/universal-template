<!-- capsule-v2 -->
# Tool-view metadata dispatch — how does a caller restrict which kernel functions the model may see, and how does that restriction reach the request?

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Given a kernel full of plugins, how do you expose only a subset of functions to the model, and where does that subset get installed into the outgoing request settings?

## Singledispatch over bool/dict shapes
**Path/Symbol:** `python/semantic_kernel/functions/kernel_function_extension.py:KernelFunctionExtension.get_list_of_function_metadata` (341–413; bool overload 348–368, dict overload 370–413); sibling `get_full_list_of_function_metadata` (337–339).
**Signature:** `@singledispatchmethod def get_list_of_function_metadata(self, *args: Any, **kwargs: Any) -> list[KernelFunctionMetadata]`.
**Data Shape:** bool overload takes `include_prompt`/`include_native` (both default True) and filters by `func.is_prompt`; dict overload takes up to four keys — `included_plugins`, `excluded_plugins`, `included_functions`, `excluded_functions` (each `list[str]`). Function-level matching is against `fully_qualified_name` (`plugin-function`), so bare names only match plugin-less functions. An empty plugin collection short-circuits to `[]` in both overloads; any other first-argument type hits the base implementation and raises `NotImplementedError`.

### Decisive source
```python
if included_plugins and excluded_plugins:
    raise ValueError("Cannot use both included_plugins and excluded_plugins at the same time.")
if included_functions and excluded_functions:
    raise ValueError("Cannot use both included_functions and excluded_functions at the same time.")
result: list[KernelFunctionMetadata] = []
for plugin_name, plugin in self.plugins.items():
    if plugin_name in excluded_plugins or (included_plugins and plugin_name not in included_plugins):
        continue
    for function in plugin:
        if function.fully_qualified_name in excluded_functions or (
            included_functions and function.fully_qualified_name not in included_functions
        ):
            continue
        result.append(function.metadata)
return result
```

**Flow:** validate mutual exclusion first (hard error, not silent precedence); walk plugins in registry order; exclusion is checked before inclusion at each level; absent keys mean "no constraint" (`excluded_*` default `[]`, `included_*` default None); surviving functions contribute their metadata object (not a copy).
**Invariant:** included/excluded are mutually exclusive PER LEVEL (plugins vs functions are independent); function filters match FQNs, never bare names; the bool overload's two flags can both be False, which yields an empty list rather than an error.
**Probe:** `python/tests/unit/services/test_service_utils.py::test_string_schema_throws_included_and_excluded_plugins` (218–225) and `::test_string_schema_throws_included_and_excluded_functions` (227–234); `::test_string_schema_filter_functions` (210–216, `included_functions=["random"]` → `[]`); `::test_bool_schema_no_plugins` (164–169, `kernel.plugins = None` → `[]`).
**Coverage caveat:** Codebase Memory MCP not connected this session; whole-file direct reads used instead of graph snippets (recorded in verification.md).

## Behavior → settings callback plumbing
**Path/Symbol:** `python/semantic_kernel/connectors/ai/function_choice_behavior.py:FunctionChoiceBehavior.configure` (90–108), `_check_and_get_config` (75–88), `from_dict` (181–207), `from_string` (209–220); `DEFAULT_MAX_AUTO_INVOKE_ATTEMPTS = 5` (18).
**Signature:** `def configure(self, kernel, update_settings_callback: Callable[..., None], settings: PromptExecutionSettings) -> None`.
**Data Shape:** `filters` field carries the same four-key dict as the dict overload; `type_` is a `FunctionChoiceType` (auto/none/required); the attempt budget lives in `maximum_auto_invoke_attempts` (Auto→5, Required→1, NoneInvoke→0) and `auto_invoke_kernel_functions` derives from `> 0`.

### Decisive source
```python
if not self.enable_kernel_functions:
    return
config = self.get_config(kernel)          # filters ? get_list_of_function_metadata(filters) : FULL list
if config:
    update_settings_callback(config, settings, self.type_)
# from_dict: dotted names become hyphenated FQNs before merging into existing filters
valid_fqns = [name.replace(".", "-") for name in functions]
if filters:
    filters = _combine_filter_dicts(filters, {"included_functions": valid_fqns})
else:
    filters = {"included_functions": valid_fqns}
```

**Flow:** `configure` is a no-op when `enable_kernel_functions=False` (checked BEFORE any kernel access); otherwise it builds a `FunctionCallChoiceConfiguration(available_functions=...)` from filtered-or-full metadata and hands it to the caller-supplied callback together with `settings` and `self.type_` — the behavior object itself never mutates settings. The callback (`update_settings_from_function_call_configuration`, see `function-call-schema-projection`) is what installs `tool_choice` + `tools`. `from_dict` converts dotted names to hyphenated FQNs and merges them into pre-existing filters via `_combine_filter_dicts` (order-preserving dedupe; a non-list value raises `ServiceInitializationError`). `from_string` accepts only `auto`/`none`/`required` case-insensitively, else `ServiceInitializationError`.
**Invariant:** the disable switch short-circuits before touching the kernel; the model-visible set is decided ONCE at configure time (not per tool call); `functions` in a dict config is sugar for `included_functions`, unioned with any explicit filters.
**Probe:** `python/tests/unit/connectors/ai/test_function_choice_behavior.py::test_configure_auto_invoke_kernel_functions_skip` (150–154, callback NOT called when disabled); `::test_auto_function_choice_behavior_from_dict_with_different_filters_and_functions` (82–96, filters ∪ functions); `::test_service_initialization_error` (204–209, non-list filter value); `::test_from_string_invalid` (227–232).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "get_list_of_function_metadata filters included_functions fully_qualified_name FunctionChoiceBehavior configure", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; recorded as degraded retrieval, command kept byte-for-byte for the next connected pass.)

## Verdict
Adopt the shape-dispatch contract (bool flags vs four-key filter dict), the per-level mutual-exclusion hard errors, FQN-based function matching, and the "behavior decides the set, callback installs it into settings" split. Adapt the four-key vocabulary and the dot→hyphen FQN convention to your host's naming scheme. Omit the `NotImplementedError` base dispatch — raise an explicit unsupported-shape error at your API boundary instead.
