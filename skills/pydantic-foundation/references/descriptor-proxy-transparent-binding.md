<!-- capsule-v2 -->
# PydanticDescriptorProxy transparent binding — how do decorator wrappers stay invisible as class attributes while staying detectable?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** How can a decorator result wrap a classmethod/staticmethod/property yet behave identically on attribute access, and when must it auto-promote to classmethod?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_decorators.py:PydanticDescriptorProxy` (:155-203) + `ensure_classmethod_based_on_signature`/:757-770 + `_is_classmethod_from_sig` :773-778.
**Signature:** `PydanticDescriptorProxy(Generic[ReturnType])` dataclass (NO slots): `(wrapped: DecoratedType, decorator_info: DecoratorInfo, shim=None)`; `__get__(self, obj, obj_type=None) -> PydanticDescriptorProxy`.
**Data Shape:** `wrapped` is a classmethod/staticmethod/property/plain callable; `decorator_info` is one of the `*DecoratorInfo` dataclasses; `shim` adapts v1-style functions.

### Decisive source
```python
def __post_init__(self):
    for attr in 'setter', 'deleter':
        if hasattr(self.wrapped, attr):
            f = partial(self._call_wrapped_attr, name=attr)
            setattr(self, attr, f)

def _call_wrapped_attr(self, func, *, name):
    self.wrapped = getattr(self.wrapped, name)(func)
    if isinstance(self.wrapped, property):
        from ..fields import ComputedFieldInfo
        if isinstance(self.decorator_info, ComputedFieldInfo):
            self.decorator_info.wrapped_property = self.wrapped
    return self

def __get__(self, obj, obj_type=None):
    try:
        return self.wrapped.__get__(obj, obj_type)
    except AttributeError:
        # not a descriptor, e.g. a partial object
        return self.wrapped

def __getattr__(self, name, /):
    """Forward checks for __isabstractmethod__ and such."""
    return getattr(self.wrapped, name)

# promotion at decoration time (functional_validators.field_validator.dec):
if _decorators.is_instance_method_from_sig(f):
    raise PydanticUserError(..., code='validator-instance-method')
f = _decorators.ensure_classmethod_based_on_signature(f)

def ensure_classmethod_based_on_signature(function):
    if not isinstance(unwrap_wrapped_function(function, unwrap_class_static_method=False), classmethod) \
            and _is_classmethod_from_sig(function):
        return classmethod(function)
    return function
```

**Flow:** decorator factory builds info → wraps result in proxy → class body stores proxy under the function name → namespace inspection detects it by type (`collect_model_fields`/`set_model_fields` are graph callers of `__get__`) → runtime attribute access delegates to wrapped descriptor; later `@name.setter`/`.deleter` re-wrap in place and keep `ComputedFieldInfo.wrapped_property` pointing at the NEW property.
**Invariant:** The proxy must be transparent (`__get__`/`__set_name__`/`__getattr__` all forward) or dunder probes like `__isabstractmethod__` break; slots must stay OFF because `__post_init__` sets instance attrs; auto-classmethod triggers ONLY on first-param-name `cls` AND not-already-classmethod — first param `self` raises instead.
**Probe:** `tests/test_computed_fields.py::test_computed_fields` (:130-150) — after `@area.setter`, `Square.model_computed_fields['area'].wrapped_property is Square.area`; `tests/test_validators.py::test_wildcard_validators` (:730-761) defines validators WITHOUT `@classmethod` and they still bind.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "PydanticDescriptorProxy __get__ ensure_classmethod_based_on_signature", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-branch `__get__`, forwarded dunders, setter/deleter re-wrap with `wrapped_property` sync, and signature-based implicit classmethod promotion; adapt the `validator-instance-method` error policy to your host's decorator set; omit the v1 `shim` plumbing if you have no legacy API.
