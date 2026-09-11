<!-- capsule-v2 -->
# lexical closure recursion — how is a function's full dependency source extracted as standalone code?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** How do I turn a function + its transitive globals into a self-contained, re-executable source file for prompt versioning?

## depth-first closure over dill-derived names
**Path/Symbol:** `src/ell/util/closure.py:lexical_closure` (:50-114) with helpers `_get_globals_and_frees` (:125-136), `_process_dependencies` (:138-150), `_process_variable` (:197-214), `_process_module`/`_process_modules` (:231-287), `_process_other_variable` (:238-245), `_build_final_source` (:289-293), `_clean_src` (:395-417), `get_referenced_names` (:318-344).
**Signature:** `lexical_closure(func, already_closed=None, initial_call=False, recursion_stack=None, forced_dependencies=None) -> Tuple[str, Tuple[str, str], Set]`.
**Data Shape:** returns `(dirty_src, (source, dependencies_source), uses_set)`; DELIM-separated section file; wrapper attrs set via `_update_ell_func` → `__ell_closure__ = (formatted_source, formatted_dsrc, globals_dict, frees_dict)`.

### Decisive source
```python
# closure.py:238-245 — mutable values become honest placeholders, not copies
def _process_other_variable(var_name, var_value, dependencies, uses):
    if isinstance(var_value, str) and '\n' in var_value:
        dependencies.append(f"{var_name} = '''{var_value}'''")
    elif is_immutable_variable(var_value):
        dependencies.append(f"# <BV>\n{var_name} = {repr(var_value)}\n# </BV>")
    else:
        dependencies.append(f"# <BmV>\n{var_name} = <{type(var_value).__name__} object>\n# </BmV>")
```

```python
# closure.py:251-266 — module deps inline ONLY the referenced attributes
while modules:
    mname, mval = modules.popleft()
    attrs_to_extract = get_referenced_names(cur_src.replace(DELIM, ""), mname)
    ...
    cur_src = _dereference_module_names(cur_src, mname, attrs_to_extract)
```

**Flow:** unwrap `__ell_func__` layers → `dill.source.getsource(lstrip=True, force=True)` → collect globals (`globalvars`, recursing through closures/nested code) and frees (`dill.detect.freevars`) → classify each name: importable module/attr → import line; function/class/module in local tree → recursive `lexical_closure` (with `already_closed` id-set and a recursion stack for error traces); builtin → skip; immutable literal → `<BV>` tagged repr line; anything else → `<BmV>` placeholder naming the type. Module objects are queued, their *referenced attributes* found by AST walk (`ast.Attribute` where value.id == module name), inlined, then dereferenced in source. Final assembly sorts imports/modules/deps separately, dedupes preserving order, strips duplicates, hoists all import lines to the top (`_clean_src`), and Black-formats (failure-tolerant fallback to raw).
**Invariant:** FORBIDDEN_NAMES `["ell", "lstr"]` are never closed over (the framework must not inline itself); mutable state is never silently serialized as if current — it becomes an explicit `<BmV>` marker so version diffs expose mutability instead of hiding it.
**Probe:** `tests/test_closure.py:test_lexical_closure_with_global` (:27-35) pins `"global_var = 10" in result`; `test_lexical_closure_with_nested_function` (:36-45) pins inner defs inlined; `test_lexical_closure_uses` (:117-137) pins `__ell_uses__` population and hash prefixes.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "lexical closure source", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.util.closure.lexical_closure @ src/ell/util/closure.py:50-114
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "referenced names module attribute", limit: 3, fields: ["signature", "name", "file"] });
// rank-1: get_referenced_names @ src/ell/util/closure.py:318-344
```

## Verdict
Adopt the classification ladder and the `<BV>/<BmV>` honesty markers wholesale — they are what makes stored versions diffable truth. Adapt the AST attribute-extraction to your parser of choice. Omit the vendored dill `globalvars` copy at file bottom only if you can depend on upstream dill behavior staying stable.
