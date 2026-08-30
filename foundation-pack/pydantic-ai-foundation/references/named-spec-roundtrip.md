<!-- capsule-v2 -->
# NamedSpec short-form round-trip — three serialization forms and the dict-ambiguity carve-out

## Source / Question
`pydantic_ai_slim/pydantic_ai/_spec.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you let YAML/JSON configs name a class with zero args, one positional arg, or kwargs — and round-trip that WITHOUT mistaking a single dict positional argument for a kwargs bag on the way back? A porter will use the compact `{Name: value}` form unconditionally and corrupt `ModelSettings`-style single-dict args.

## Path / Symbol
`_spec.py` — `NamedSpec(BaseModel)` (:50–110), `_SerializedNamedSpec(RootModel)` (:113–148), `serializes_as_string_keyed_dict()` (:37–47), `build_registry()` (:159–197), `load_from_registry()` (:200–236), `filter_serializable_type()` (:239–270), `build_schema_types()` (:273–337).

## Signature
```python
class NamedSpec(BaseModel):
    name: str
    arguments: None | tuple[Any] | dict[str, Any]   # 3 internal shapes
    @property args -> tuple; kwargs -> dict
    @model_validator(mode='wrap') deserialize(value, handler)   # accepts short forms in
    @model_serializer(mode='wrap') serialize(self, handler, info)  # emits short forms out
```

## Data Shape
Three short forms: `'MyClass'` (no args), `{'MyClass': value}` (single positional), `{'MyClass': {k:v}}` (kwargs). Internally `arguments` is `None`, `(value,)`, or `{...}`. Deserialization tries the typed model FIRST and falls back to `_SerializedNamedSpec` only on ValidationError, re-raising the ORIGINAL error if both fail (never the fallback's error).

### Decisive source — the ambiguity carve-out (:96–110)
```python
if isinstance(info.context, dict) and info.context.get('use_short_form'):
    if self.arguments is None:
        return self.name
    elif isinstance(self.arguments, tuple):
        # A single positional arg that serializes as a string-keyed dict would be
        # misinterpreted as kwargs on deserialization. Fall back to the long form.
        if serializes_as_string_keyed_dict(self.arguments[0]):
            return handler(self)
        return {self.name: self.arguments[0]}
    else:
        return {self.name: self.arguments}
```
The mirror-side heuristic (`_SerializedNamedSpec._args` :133–145): a dict value whose keys are ALL strings is treated as kwargs; anything else (list, scalar, mixed-key dict) becomes `(value,)`. Short-form emission only fires when `context['use_short_form']` is set — default dumps stay long-form.

**Flow:** validate → try native form → fallback parses short forms (one-key dicts enforced loudly) → instantiate via `load_from_registry(cls(*args, **kwargs)` or an injected `instantiate` callback, wrapping failures as `ValueError('Failed to instantiate {label} ...')` naming the registry key. Schema generation walks `from_spec`/`__init__` hints, drops TypeVars/Callables via `filter_serializable_type`, wraps defaults as NotRequired, and emits Literal/short-spec/full-spec union members per arity.

**Invariant:** The compact `{name: value}` form may be emitted ONLY when `serializes_as_string_keyed_dict(value)` is false; deserialization's all-string-keys ⇒ kwargs rule is fixed and cannot be negotiated. Registry semantics: custom types override defaults silently (`setdefault`), duplicate custom names raise, opted-out names (None) raise only for customs.

**Probe:** `tests/test_spec.py` — serialize/deserialize matrix :14–93 (`test_single_non_string_arg` :35, `test_single_list_arg` :40, `test_serialize_short_form_kwargs` :64), registry :93–167 (`test_custom_overrides_default` :111, `test_opted_out_custom_raises` :143), schema types :223+ (`test_no_params_class` :223).

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'NamedSpec _SerializedNamedSpec build_schema_types load_from_registry'
```

## Verdict
**Adopt** NamedSpec wholesale as the config-to-constructor protocol for any plugin/capability registry. **Adopt** the string-keyed-dict long-form fallback verbatim — it is the entire point of the module. **Adapt** the label/custom_types_param error vocabulary to your domain. **Omit** the pydantic-specific wrap validator mechanics only if your host lacks an equivalent hook (then implement the same two-sided heuristic by hand).
