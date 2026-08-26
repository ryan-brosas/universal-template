<!-- capsule-v2 -->
# Private-attr init + `model_post_init` wrapping — when does the metaclass rewrite `model_post_init`, and why only when privates exist?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `ext-pydantic`. **Question:** How are private attribute defaults initialized per-instance, and what is the exact condition for wrapping a user's `model_post_init`?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_model_construction.py:init_private_attributes` (:361-382), `get_model_post_init` (:385-394), metaclass wiring (:221-240).
**Signature:** `def init_private_attributes(self: BaseModel, context: Any, /) -> None` (called BY pydantic-core with context as 2nd positional arg).
**Data Shape:** `__private_attributes__: dict[str, ModelPrivateAttr]`; defaults may be factories that take validated data.

### Decisive source
```python
# in ModelMetaclass.__new__, AFTER set_model_fields:
if cls.__private_attributes__:
    original_model_post_init = get_model_post_init(namespace, bases)
    if original_model_post_init is not None:
        @wraps(original_model_post_init)
        def wrapped_model_post_init(self: BaseModel, context: Any, /) -> None:
            """We need to both initialize private attributes and call the user-defined model_post_init method."""
            init_private_attributes(self, context)
            original_model_post_init(self, context)
        cls.model_post_init = wrapped_model_post_init
    else:
        cls.model_post_init = init_private_attributes

cls.__pydantic_post_init__ = (
    None if cls.model_post_init is BaseModel_.model_post_init else 'model_post_init'
)

# init_private_attributes:
if getattr(self, '__pydantic_private__', None) is None:
    pydantic_private = {}
    for name, private_attr in self.__private_attributes__.items():
        if private_attr.default_factory_takes_validated_data:
            default = private_attr.get_default(call_default_factory=True, validated_data={**self.__dict__, **pydantic_private})
        else:
            default = private_attr.get_default(call_default_factory=True)
        if default is not PydanticUndefined:
            pydantic_private[name] = default
    object_setattr(self, '__pydantic_private__', pydantic_private)
```

**Flow:** If the class has ANY private attributes: look up `model_post_init` (namespace first, else nearest base that isn't BaseModel's no-op); wrap it (privates-init THEN user hook) or substitute `init_private_attributes` directly. Record whether a custom post-init exists in `__pydantic_post_init__` ('model_post_init' or None) — pydantic-core reads this to decide whether to invoke it after validation.
**Invariant:** Without private attributes the user's `model_post_init` is NOT wrapped and remains untouched (zero overhead). Factories needing validated data receive `{**self.__dict__, **pydantic_private}` progressively — earlier privates ARE visible to later factory calls. Init uses `object_setattr` to bypass `BaseModel.__setattr__` validation.
**Probe:** `grep -n 'wrapped_model_post_init' pydantic/_internal/_model_construction.py` (:227/:234 — the wrap-or-substitute pair pins the conditional-wrapping invariant).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic", query: "init_private_attributes model_post_init wrapped", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the conditional-wrap pattern (hook composition only when state needs initializing) and the progressive validated-data dict; adapt `object_setattr` bypass naming; omit pydantic-core's `__pydantic_post_init__` consumption details.
