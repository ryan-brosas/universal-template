<!-- capsule-v2 -->
# TypeAdapter lazy core attrs — which caller frame owns forward-ref resolution, and what does `_init_core_attrs` reuse before generating?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** How does a standalone type adapter resolve annotations from the instantiation site, and when does it rebuild vs reuse a type's existing core attrs?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/type_adapter.py:TypeAdapter.__init__` (:194-248), `_fetch_parent_frame` :250-259, `_init_core_attrs` :261-331, `rebuild` :350-394.
**Signature:** `TypeAdapter(type, *, config=None, _parent_depth=2, module=None)`; `_init_core_attrs(ns_resolver, force, raise_errors=False) -> bool`; `rebuild(*, force=False, raise_errors=True, ...) -> bool | None`.
**Data Shape:** instance attrs `core_schema`, `validator`, `serializer`, `pydantic_complete: bool`; tri-state rebuild return `None | True | False`.

### Decisive source
```python
frame = sys._getframe(self._parent_depth)
if frame.f_globals.get('__name__') == 'typing':
    # Because `TypeAdapter` is generic, explicitly parametrizing the class results
    # in a `typing._GenericAlias` ... adding an extra frame to the call:
    return frame.f_back

...
try:
    self.core_schema = _getattr_no_parents(self._type, '__pydantic_core_schema__')
    self.validator  = _getattr_no_parents(self._type, '__pydantic_validator__')
    self.serializer = _getattr_no_parents(self._type, '__pydantic_serializer__')
    if (isinstance(self.core_schema, MockCoreSchema)
            or isinstance(self.validator, MockValSer)
            or isinstance(self.serializer, MockValSer)):
        raise AttributeError()          # mocks ⇒ force regeneration below
except AttributeError:
    ...GenerateSchema(config_wrapper, ns_resolver).generate_schema(self._type)...   # PydanticUndefinedAnnotation → mocks unless raise_errors

# rebuild(): manual globals fetch — no type on the NsResolver stack:
globalns = sys._getframe(max(_parent_namespace_depth - 1, 1)).f_globals
return self._init_core_attrs(ns_resolver=..., force=True, raise_errors=raise_errors)
```

**Flow:** init → config-vs-model guard (`type-adapter-config-unused`) → parent-frame capture at depth 2 with the typing-proxy hop-back → functions use `ns_for_function`, everything else uses frame locals/globals (locals dropped at module level) → `_init_core_attrs(force=False)`: `defer_build` installs the mock trio and returns False; otherwise try REUSING the adapted type's own dunder core attrs; any Mock present forces fresh generation; generation failure downgrades to mocks when `raise_errors=False`.
**Invariant:** reuse only via `_getattr_no_parents` (inherited attrs from a parent class must not leak); one Mock anywhere invalidates all three; `rebuild()` returning None means "already complete, untouched" — porters must keep the tri-state because mock handlers test `is not False`.
**Probe:** `tests/test_type_adapter.py::test_core_schema_respects_defer_build` :612-652 (mocks installed under defer_build, usage builds exactly once); `::test_defer_build_raise_errors` :655-669 (raise/soft/success ladder); `::test_correct_frame_used_parametrized` :683-696 (`TypeAdapter[int]('Any')` resolves caller-module `Any = int`, not `typing.Any`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "TypeAdapter _init_core_attrs _fetch_parent_frame defer_build", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt frame-depth namespace capture with the generic-alias hop-back, reuse-then-generate attr ladder, and tri-state rebuild; adapt `_parent_depth` magic numbers to your call convention; omit FastAPI-style Annotated `_model_config` probing if your host lacks it.
