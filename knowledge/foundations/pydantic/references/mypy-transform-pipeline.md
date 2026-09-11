<!-- capsule-v2 -->
# PydanticModelTransformer.transform — how does the mypy plugin synthesize `__init__` and `model_construct`, and when does it defer?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** What is the plugin's transform pipeline, what triggers `defer()` for another semanal pass, and how is metadata serialized into TypeInfo?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/mypy.py:PydanticModelTransformer.transform` (:520-559).
**Signature:** `def transform(self) -> bool` (False ⇒ mypy runs another pass).
**Data Shape:** Writes `info.metadata[METADATA_KEY] = {'fields': {name: serialize()}, 'class_vars': {...}, 'config': get_values_dict()}` — the inheritance channel read by `collect_config`/`collect_fields_and_class_vars` of SUBCLASSES.

### Decisive source
```python
info = self._cls.info
is_a_root_model = is_root_model(info)
config = self.collect_config()
fields, class_vars = self.collect_fields_and_class_vars(config, is_a_root_model)
if fields is None or class_vars is None:
    return False                       # some definitions are not ready → another pass
for field in fields:
    if field.type is None or has_placeholder(field.type):
        if not self._api.final_iteration:
            self._api.defer()          # forward refs / generics not resolved yet
        return False

is_settings = info.has_base(BASESETTINGS_FULLNAME)
self.add_initializer(fields, config, is_settings, is_a_root_model)      # fields-aware __init__
self.add_model_construct_method(fields, config, is_settings, is_a_root_model)  # validation-free ctor
self.set_frozen(fields, self._api, frozen=config.frozen is True)        # Var.is_property on fields
self.adjust_decorator_signatures()     # mark validator/serializer funcs as classmethods (except mode='after')
info.metadata[METADATA_KEY] = {
    'fields': {field.name: field.serialize() for field in fields},
    'class_vars': {cv.name: cv.serialize() for cv in class_vars},
    'config': config.get_values_dict(),
}
return True
```

**Flow:** collect config (class kwargs + `model_config` + legacy Config class; MRO-setdefault from ancestors' METADATA_KEY with wildcard plugin-dependency triggers) → collect fields walking reversed MRO then current body (`_get_assignment_statements_from_block` descends IfStmt branches that aren't unreachable) → bail/defer on placeholders → synthesize methods → freeze → persist metadata.
**Invariant:** Deferral must happen BEFORE any signature synthesis or the wrong `__init__` sticks. Serialized field types ride through `deserialize_and_fixup_type` so cached runs rehydrate types against the CURRENT api. `add_initializer` skips if a user-defined `__init__` exists UNLESS it's plugin-generated or the class IS RootModel (plugin wins over RootModel's checker-only stub). Settings subclasses get BaseSettings' private-ish args appended as ARG_OPT with an explicit-Any rewrite via `ChangeExplicitTypeOfAny`.
**Probe:** `grep -n 'def transform' pydantic/mypy.py` (:520) + `grep -n 'self._api.defer()' pydantic/mypy.py` (:543/:1038 — both deferral sites).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "PydanticModelTransformer transform add_initializer", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the collect→defer→synthesize→persist pipeline and metadata-as-inheritance-channel design; adapt to your checker's plugin API; omit BaseSettings-specific arg surgery.
