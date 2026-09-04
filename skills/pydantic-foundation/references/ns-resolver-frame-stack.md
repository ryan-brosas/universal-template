<!-- capsule-v2 -->
# NsResolver frame stack — how are forward-ref evaluation namespaces built while a class is still being defined?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When schema generation evaluates a string annotation, which globals/locals does it use, and how does the resolver let a class see its own name before the class object exists in module globals?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_namespace_utils.py:NsResolver` (:143-293), `LazyLocalNamespace` :66-103, `ns_for_function` :106-140, `get_module_ns_of` :48-61. Push call sites: `_generate_schema.py` :838 (model), :1368 (TypeAliasType), :1897 (dataclass); `ns_for_function` feeds `type_adapter.py` :226 and `_validate_call.py` :84.
**Signature:** `NsResolver(namespaces_tuple: NamespacesTuple | None = None, parent_namespace: MappingNamespace | None = None)`; `push(self, typ, /) -> Generator[None]` (context manager); `types_namespace -> NamespacesTuple` (cached_property).
**Data Shape:** a stack of types being inspected; `types_namespace` yields `(globals, locals)` for `eval` — globals is the LIVE module dict of the top type (not a copy), locals is a lazily-merged mapping.

### Decisive source
```python
@contextmanager
def push(self, typ: type[Any] | TypeAliasType, /) -> Generator[None]:
    self._types_stack.append(typ)
    self.__dict__.pop('types_namespace', None)   # invalidate the cached property
    try:
        yield
    finally:
        self._types_stack.pop()
        self.__dict__.pop('types_namespace', None)

# types_namespace (stack non-empty), locals assembled in ASCENDING priority:
if self._parent_ns is not None:
    locals_list.append(self._parent_ns)          # lowest — applied to EVERY pushed type (back-compat flaw)
if len(self._types_stack) > 1:
    first_type = self._types_stack[0]
    locals_list.append({first_type.__name__: first_type})   # nested types see the outermost model name
type_params = getattr(typ, '__type_params__', ())           # PEP 695
if type_params:
    locals_list.append({t.__name__: t for t in type_params})
if hasattr(typ, '__dict__'):                        # TypeAliasType has no __dict__
    locals_list.append(vars(typ))
locals_list.append({typ.__name__: typ})             # highest — self-reference before class lands in globals
return NamespacesTuple(globalns, LazyLocalNamespace(*locals_list))
```

**Flow:** schema generation pushes each class/dataclass/alias it inspects → inside the with-block, `types_namespace` is computed once (cached) from the TOP of the stack: globals = that type's module namespace; locals = parent_ns → outermost-type name → PEP 695 type params → the type's own vars → its own name, later entries shadowing earlier ones → on pop, both the stack entry and the cached namespace are discarded so the next sibling recomputes cleanly. Function-shaped surfaces skip the stack entirely: `ns_for_function` returns (module globals, LazyLocalNamespace(parent_ns, {t.__name__ for t in function+class `__type_params__`})).
**Invariant:** the pushed type's own name is ALWAYS in locals at highest priority — this is what makes self-referential annotations resolve during definition, when the name is not yet in module globals; the cache invalidation must happen on BOTH push and pop (a stale cache after pop would leak one class's locals into the next); `get_module_ns_of` returns the live dict and its docstring puts the no-mutation burden on the caller; the parent-namespace-applies-to-every-pushed-type behavior is a documented backwards-compat flaw pinned by xfail tests (`test_forward_ref.py` :1449, :1629).
**Probe:** `tests/test_forward_ref.py::test_lazy_local_namespace_len` :1141-1144 (merged lazy namespace reports union size 2, not 3) and `::test_uses_the_local_namespace_when_generating_schema` :1276-1292 (a function-local `A = int` resolves a deferred `'dict[str, A]'` annotation at rebuild time even though a module-level `A = str` exists afterwards).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "NsResolver push types_namespace LazyLocalNamespace ns_for_function", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the push/pop frame stack with dual cache invalidation, the ascending-priority locals assembly ending in the type's own name, and the empty-stack base-tuple fallback for adapter-style surfaces; adapt the parent-namespace semantics to your host's scoping rules (pydantic's every-type application is a known wart); omit the PEP 695 type-param layer if your host predates it. Caveat: Retrieve written but not executed this pass (MCP unavailable); anchors verified by direct read at the pin.
