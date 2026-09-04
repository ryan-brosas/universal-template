<!-- capsule-v2 -->
# DataPoint deterministic identity — uuid5 over class-namespaced identity_fields

**Source:** cognee (Apache-2.0) `main@a8f9760b`; Codebase Memory `ext-cognee`. **Question:** How do graph nodes get stable ids so a re-mentioned entity merges across runs, without every model being forced to declare identity?

## DataPoint.__init__ + id_for
**Path/Symbol:** `cognee/infrastructure/engine/models/DataPoint.py:DataPoint.__init__` (:69-88), `id_for` (:176-191), `_normalize_identity_value` (:160-168), `__pydantic_init_subclass__` (:193-220).
**Signature:** `id: UUID = Field(default_factory=uuid4)`; `@classmethod id_for(cls, *values) -> UUID`; metadata contract `{"index_fields": [...], "identity_fields": [...]}`.
**Data Shape:** Random id = NO stable identity (never dedups/merges). Declaring `identity_fields` opts a subclass into determinism.

### Decisive source
```python
joined = "|".join(cls._normalize_identity_value(v) for v in values)
return uuid5(NAMESPACE_OID, f"{cls.__name__}:{joined}")

@staticmethod
def _normalize_identity_value(value):
    if isinstance(value, str):
        return value.lower().replace(" ", "_").replace("'", "")
    return str(value)   # byte-for-byte aligned with legacy generate_node_id hashing
```

**Flow:** `__init__` records whether an explicit id was passed → after validation, if none, `_get_identity_fields()` reads them from the class's metadata default (walking the MRO to warn when a subclass override DROPS a parent's identity_fields) → `_generate_identity_id` collects values from instance `__dict__` (no model_dump — hot path) falling back to field defaults; any missing field ⇒ None ⇒ fall back to random uuid4.
**Invariant:** (1) The namespace is the CLASS NAME — two node types can never collide on the same string, and callers can't mistype the prefix. (2) `id_for` is the single source of truth used BOTH at construction and at raw-string lookup (`Entity.id_for(name)` before an instance exists); `_generate_identity_id` delegating to it is what guarantees they never drift. (3) Normalization must stay aligned with legacy name-hashing or historical ids become unrecomputable (pinned by TestNormalizationMatchesGenerateNodeId). (4) Annotated markers auto-derive metadata in `__pydantic_init_subclass__` ONLY when the subclass didn't declare metadata itself.
**Probe:** `cognee/tests/unit/infrastructure/engine/test_identity_fields.py` (29 tests: `test_same_name_different_class_different_id`, `test_id_for_namespaced_by_class`, `test_subclass_dropping_identity_fields_logs_warning`, normalization pins).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-cognee", query: "DataPoint _get_identity_fields id_for uuid5 NAMESPACE_OID normalize", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt class-namespaced uuid5 identity with opt-in fields and shared normalization; adapt field sets to your entity model; omit cognee's Annotated-marker sugar if your models are explicit.
