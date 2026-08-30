<!-- capsule-v2 -->
# MockValSer/MockCoreSchema lazy-rebuild proxies — how do deferred builds fail loudly only at first USE?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What must a placeholder validator/serializer do when any attribute is touched, and where does the rebuild attempt hook in?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_mock_val_ser.py:MockValSer.__getattr__` (:91-100), `MockCoreSchema._get_built` (:49-58).
**Signature:** `class MockValSer(Generic[ValSer])` with `__getattr__(self, item: str) -> None`; `MockCoreSchema(Mocking Mapping[str, Any])`.
**Data Shape:** Slots `_error_message`, `_code` (`PydanticErrorCodes`), `_val_or_ser` (the REAL class for attribute-existence checks), `_attempt_rebuild: Callable[[], ValSer | None] | None`; MockCoreSchema adds `_built_memo`.

### Decisive source
```python
def __getattr__(self, item: str) -> None:
    __tracebackhide__ = True
    if self._attempt_rebuild:
        val_ser = self._attempt_rebuild()
        if val_ser is not None:
            return getattr(val_ser, item)
    # raise an AttributeError if `item` doesn't exist
    getattr(self._val_or_ser, item)
    raise PydanticUserError(self._error_message, code=self._code)

class MockCoreSchema(Mapping[str, Any]):
    def _get_built(self) -> CoreSchema:
        if self._built_memo is not None:
            return self._built_memo
        if self._attempt_rebuild:
            schema = self._attempt_rebuild()
            if schema is not None:
                self._built_memo = schema
                return schema
        raise PydanticUserError(self._error_message, code=self._code)
```

**Flow:** Class creation under `defer_build`/failed completion installs mocks into `__pydantic_core_schema__/validator/serializer` (models), the same trio (dataclasses via `rebuild_dataclass`), or `adapter.core_schema/validator/serializer` (`set_type_adapter_mocks`). First real USE (any method access / any mapping access): attempt rebuild via the injected callable → success returns the attribute of the FRESHLY BUILT object (validator methods are NOT re-bound onto the mock; every call re-resolves until replaced) → failure raises `PydanticUserError('...is not fully defined; ... call .model_rebuild()/.rebuild()...', code='class-not-fully-defined')`.
**Invariant:** Two-step error shaping in `MockValSer.__getattr__`: first `getattr(self._val_or_ser, item)` against the REAL SchemaValidator/SchemaSerializer CLASS so genuinely missing attributes surface as AttributeError, THEN the user-facing PydanticUserError — porters who skip step one mask typos as "not fully defined". Rebuild handlers close over `_parent_namespace_depth=5` (frame-walk depth matters). MockCoreSchema memoizes successful rebuilds; MockValSer deliberately does not.
**Probe:** `grep -c "code='class-not-fully-defined'" pydantic/_internal/_mock_val_ser.py` (9 — three mock slots × model/dataclass/TypeAdapter installers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "MockValSer __getattr__ attempt_rebuild PydanticUserError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the proxy contract (lazy attempt → loud coded error → two-step attr check); adapt error message wording to your API's rebuild entry points; omit plugin-aware PluggableSchemaValidator interplay.
