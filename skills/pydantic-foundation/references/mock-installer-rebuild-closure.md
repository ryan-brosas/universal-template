<!-- capsule-v2 -->
# Mock-installer rebuild closure — what exactly do the model/dataclass/TypeAdapter mock installers hand each mock as its rebuild hook?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** When a deferred-build surface installs mocks, how is the rebuild attempt wired per surface, and why does the depth magic differ from the caller's own rebuild?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_mock_val_ser.py:set_type_adapter_mocks` (:112-148), `set_model_mocks` :151-189, `set_dataclass_mocks` :192-232.
**Signature:** `set_*_mocks(target) -> None`, installing one MockCoreSchema + two MockValSers; shared inner factory `attempt_rebuild_fn(attr_fn: Callable[[T], U]) -> Callable[[], U | None]`.
**Data Shape:** three slots per surface (`core_schema`/`__pydantic_core_schema__`, validator, serializer) all sharing ONE error message and code `'class-not-fully-defined'`.

### Decisive source
```python
def set_type_adapter_mocks(adapter: TypeAdapter) -> None:
    type_repr = str(adapter._type)
    undefined_type_error_message = (
        f'`TypeAdapter[{type_repr}]` is not fully defined; you should define `{type_repr}` and all referenced types,'
        f' then call `.rebuild()` on the instance.'
    )

    def attempt_rebuild_fn(attr_fn: Callable[[TypeAdapter], T]) -> Callable[[], T | None]:
        def handler() -> T | None:
            if adapter.rebuild(raise_errors=False, _parent_namespace_depth=5) is not False:
                return attr_fn(adapter)
            return None

        return handler

    adapter.core_schema = MockCoreSchema(undefined_type_error_message,
        code='class-not-fully-defined', attempt_rebuild=attempt_rebuild_fn(lambda ta: ta.core_schema))
    adapter.validator  = MockValSer(..., val_or_ser='validator',
        attempt_rebuild=attempt_rebuild_fn(lambda ta: ta.validator))
    adapter.serializer = MockValSer(..., val_or_ser='serializer',
        attempt_rebuild=attempt_rebuild_fn(lambda ta: ta.serializer))
# set_model_mocks:   cls.model_rebuild(raise_errors=False, _parent_namespace_depth=5) … attr_fn(cls) over dunders
# set_dataclass_mocks: rebuild_dataclass(cls, raise_errors=False, _parent_namespace_depth=5) … same trio
```

**Flow:** deferred/failed build → installer writes the mock trio onto the surface with per-surface rebuild entry point (`adapter.rebuild` / `cls.model_rebuild` / `rebuild_dataclass`) → first USE triggers handler → soft rebuild (`raise_errors=False`) at DEPTH 5 → success re-fetches the attribute through `attr_fn` (so the mock returns the REAL fresh object's member); failure yields None → mock raises the coded error.
**Invariant:** handlers test `is not False`, NOT truthiness — rebuild returning None ("already complete") must still fetch the attribute; `_parent_namespace_depth=5` accounts for mock→handler→rebuild→frame-walk stacking, deeper than a user calling rebuild directly; dataclass installer imports `rebuild_dataclass` lazily to dodge import cycles; all three installers share identical message/code shape so porters can factor one factory.
**Probe:** `grep -c "code='class-not-fully-defined'" pydantic/_internal/_mock_val_ser.py` → **9** (three slots × three installers). Behavior: `tests/test_type_adapter.py::test_core_schema_respects_defer_build` :612-652 asserts all three installed objects are Mock types and post-usage none are.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "set_type_adapter_mocks set_model_mocks set_dataclass_mocks attempt_rebuild", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt one shared closure factory parameterized by (surface, rebuild-entry-point, attr-getter); adapt the frame-depth constant to your wrapper stack; omit the lazy cross-module import if your host has no circular-import pressure.
