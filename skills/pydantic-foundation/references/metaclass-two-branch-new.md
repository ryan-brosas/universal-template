<!-- capsule-v2 -->
# Metaclass two-branch `__new__` — how does class creation differ between `BaseModel` itself and every subclass?

**Source:** pydantic MIT `main@2151025aa51263f3016502b00010b78e4481eaa1`; Codebase Memory `ext-pydantic`. **Question:** When porting the model metaclass, which setup work runs only for subclasses, and how does the code even detect "this is BaseModel being created"?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_model_construction.py:ModelMetaclass.__new__` (:89-277).
**Signature:** `def __new__(mcs, cls_name, bases, namespace, __pydantic_generic_metadata__: PydanticGenericMetadata | None = None, __pydantic_reset_parent_namespace__: bool = True, _create_model_module: str | None = None, **kwargs) -> type`.
**Data Shape:** `bases` empty tuple ⇒ BaseModel branch; non-empty ⇒ subclass branch. Keyword-only metadata params are injected by `create_generic_submodel`/`__class_getitem__`, never by users.

### Decisive source
```python
# Note `ModelMetaclass` refers to `BaseModel`, but is also used to *create* `BaseModel`, so we rely on the fact
# that `BaseModel` itself won't have any bases, but any subclass of it will, to determine whether the `__new__`
# call we're in the middle of is for the `BaseModel` class.
if bases:
    base_field_names, class_vars, base_private_attributes = mcs._collect_bases_data(bases)
    config_wrapper = ConfigWrapper.for_model(bases, namespace, kwargs)
    namespace_info = inspect_namespace(...)
    ...
    cls.__pydantic_complete__ = False  # Ensure this specific class gets completed
    ...
    if config_wrapper.defer_build:
        set_model_mocks(cls)
    else:
        complete_model_class(cls, config_wrapper, ns_resolver, raise_errors=False, create_model_module=_create_model_module)
    ...
    super(cls, cls).__pydantic_init_subclass__(**kwargs)
    return cls
else:
    # These are instance variables, but have been assigned to `NoInitField` to trick the type checker.
    for instance_slot in '__pydantic_fields_set__', '__pydantic_extra__', '__pydantic_private__':
        namespace.pop(instance_slot, None)
    namespace.get('__annotations__', {}).clear()
    return super().__new__(...)
```

**Flow:** bases-empty branch pops the three `NoInitField` sentinel slots and CLEARS the annotations dict, then plain `type.__new__`. Subclass branch: collect base data → resolve config (`ConfigWrapper.for_model` merges `model_config` + class-keyword config) → `inspect_namespace` → stash `model_config`/`__class_vars__`/`__private_attributes__` into the namespace BEFORE `super().__new__` → create class → warn on `Generic` before `BaseModel` in MRO → build `DecoratorInfos` (+config-driven decorators) → normalize generic metadata (raises `TypeError` on missing Generic parameters; special RootModel hint) → `__pydantic_complete__=False` → PEP-487 `__set_name__` for private attrs → capture parent frame namespace into `NsResolver` → `set_model_fields` → wrap/assign `model_post_init` → either `set_model_mocks` (defer_build) or `complete_model_class(raise_errors=False)` → frozen ⇒ default `__hash__` → parent `__pydantic_init_subclass__`.
**Invariant:** All field/config collection happens through the namespace dict BEFORE `super().__new__`; the class object does not exist yet, so nothing may read `cls.__dict__` until after creation. `__pydantic_complete__` starts False on EVERY subclass — completion is always an explicit later step.
**Probe:** `grep -n '__pydantic_complete__ = False' pydantic/_internal/_model_construction.py` (exactly the :202 site inside the subclass branch pins "every new subclass starts incomplete").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "ModelMetaclass __new__ namespace build", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the bases-empty detection idiom and the strict ordering (namespace mutation pre-`type.__new__`, completion post-hoc); adapt `import_cached_base_model()` lazy-import cycle-breaking to your host's DI style; omit the RootModel-specific parameter error strings and CPython issue references.
