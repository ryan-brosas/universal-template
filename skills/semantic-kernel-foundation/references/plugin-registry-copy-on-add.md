<!-- capsule-v2 -->
# Plugin registry copy-on-add — every insertion rebinds plugin_name via copy; duplicates overwrite; FQN splits on the first hyphen

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** How does a plugin registry let the same function object live under two plugins without cross-talk, what happens on duplicate names, and how are fully-qualified names parsed back?

## `_parse_or_copy` funnel + `function_copy` + hyphen FQN split
**Path/Symbol:** `python/semantic_kernel/functions/kernel_plugin.py:_validate_functions` (422–459) and `._parse_or_copy` (461–468); `python/semantic_kernel/functions/kernel_function.py:function_copy` (381–394); `python/semantic_kernel/functions/kernel_function_metadata.py` (16–17, 26–47); lookup at `kernel_function_extension.py:get_function_from_fully_qualified_function_name` (313–335).
**Signature:** `def _parse_or_copy(function, plugin_name: str) -> KernelFunction` / `def function_copy(self, plugin_name: str | None = None) -> KernelFunction`.
**Data Shape:** Plugin is a dict keyed by function name. Regexes (`utils/validation.py`): plugin name `^[0-9A-Za-z_]+$` (no hyphen), function name `^[0-9A-Za-z_-]+$` (hyphen allowed). FQN separator constant is `"-"`.

### Decisive source
```python
@staticmethod
def _parse_or_copy(function, plugin_name):
    if isinstance(function, KernelFunction):
        return function.function_copy(plugin_name=plugin_name)
    if callable(function):
        return KernelFunctionFromMethod(method=function, plugin_name=plugin_name)
    raise ValueError(...)
...
def function_copy(self, plugin_name=None):
    cop = copy(self)                      # shallow
    cop.metadata = deepcopy(self.metadata)
    if plugin_name:
        cop.metadata.plugin_name = plugin_name
    return cop
...
names = fully_qualified_function_name.split("-", maxsplit=1)
if len(names) == 1:
    plugin_name = None; function_name = names[0]
else:
    plugin_name, function_name = names[0], names[1]   # remainder keeps inner hyphens
```

**Flow:** Every insertion path (constructor list/dict/single/KernelPlugin, `__setitem__`, `set`, `add`, `update`) funnels through `_parse_or_copy`: bare callables are wrapped by `KernelFunctionFromMethod` (whose `__init__` raises `FunctionInitializationError` without the decorator marker or with an invalid name), and existing KernelFunctions are shallow-copied with DEEPCOPIED metadata and rebound plugin_name. Duplicate names silently overwrite (plain dict semantics). Lookup by FQN splits on the FIRST `-`.
**Invariant:** Copy-on-add means one function object registered in two plugins yields two independent metadata objects with different FQNs — mutating one plugin's copy never affects the other. The hyphen asymmetry makes bare hyphenated function names ambiguous in FQN lookup: `"my-func"` parses as plugin `"my"` / function `"func"`. (The dot-based `FULLY_QUALIFIED_FUNCTION_NAME` regex in validation.py is not consumed by this path.)
**Probe:** `python/tests/unit/functions/test_kernel_plugins.py::test_init_with_same_function_names` (260–288) asserts a native and a prompt function sharing a name collapse to `len(plugin.functions) == 1`; `test_set_item` (293–309) pins dict-style insertion equality; `test_kernel_function_from_method.py::test_init_invalid_name` (156–162) pins rejection of names failing the regex.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "function_copy _parse_or_copy plugin_name fully_qualified", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt copy-on-add with deep-copied metadata as the registry contract for any multi-namespace tool registry — it removes whole classes of shared-state bugs. Adapt the overwrite policy to your host only deliberately: SK's silent last-wins is intentional dict semantics. Omit nothing on the separator: either forbid hyphens in function names or make FQN parsing explicit, or lookups become lossy.
