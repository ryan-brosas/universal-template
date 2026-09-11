<!-- capsule-v2 -->
# single-arg tool schema — how can a one-parameter tool accept the model's unwrapped object without losing the dict contract?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** For `def f(data: SomeModel)`, how does the wire schema stay flat (no `{data: ...}` envelope) while validated args remain a name-keyed dict for hooks and callers — including re-validation after a durable-exec round trip?

## `_build_schema` / `_validate_single_arg` (`_function_schema.py`)
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_function_schema.py:_build_schema` (:319-367), `_validate_single_arg` (:374-395), `_is_wrapped_single_arg` (:370-371), `single_field_name` property (:62-79); positional/`*args` mapping in `function_schema` :156-221 and `_call_args` :91-107.
**Signature:** `_build_schema(fields, var_kwargs_schema, core_config) -> (core_schema, single_arg_name | None, accepted_keys | None)`.
**Data Shape:** Single model-like arg ⇒ JSON schema IS the model's own (properties at top level, aliases resolved by pydantic); validator output is ALWAYS `{name: value}`. `accepted_keys` starts empty and is filled from the generated JSON schema's properties so the validator can distinguish genuine unwrapped input named `name` from a wrapper envelope.

### Decisive source
```python
# _function_schema.py:350-358 — wrap validator over the model's own schema
accepted_keys: set[str] = set()
return (
    core_schema.no_info_wrap_validator_function(
        partial(_validate_single_arg, name=name, accepted_keys=accepted_keys),
        td_field['schema'],
    ),
    name,
    accepted_keys,
)

# :374-395 — disambiguate unwrapped input from a serialized wrapper envelope
if not _is_wrapped_single_arg(value, name):          # plain unwrapped model input
    return {name: handler(value)}
if name not in accepted_keys:                        # 'name' isn't a real field ⇒ must be an envelope
    return {name: handler(value[name])}
try:
    return {name: handler(value)}                    # prefer the unwrapped reading…
except ValidationError:
    return {name: handler(value[name])}              # …falling back on round-trip collision

# :156-159 + 216-219 — POSITIONAL_OR_KEYWORD params BEFORE *args become positional fields
# (keyword-passing them would double-bind with unpacked *args values)
has_var_positional = any(p.kind is Parameter.VAR_POSITIONAL for p in sig.parameters.values())
...
positional_fields.append(field_name)
```

**Flow:** `function_schema` inspects the signature; single field + model-like annotation + no `**kwargs` takes the wrap-validator path; multi-arg functions get a TypedDict schema (`extra='forbid'`, or `'allow'` with an extras schema for `**kwargs`). At call time `_call_args` copies before popping (hooks later see the FULL validated dict), expands positional fields + var-positional as positional args, passes the rest as kwargs. Return schemas are computed eagerly (`_extract_return_schema_type`: no annotation/`Any`→`{}`, `None`→null, `ToolReturn[T]`→T, `Self` resolved via bound `__self__`) so Temporal sandboxes don't pay TypeAdapter cost later; unsupported types warn and fall back to unconstrained.

**Invariant:** Validated args are ALWAYS a dict keyed by parameter name — hooks and `call_tool` rely on it — even though the model never sees the wrapper. The unwrapped reading wins when both shapes validate (an `Any`-typed field makes the shapes genuinely indistinguishable; re-validation then isn't idempotent, documented as rare).

**Probe:** `tests/test_tools.py::test_args_validator_single_base_model_arg` (:4372), `::test_single_base_model_arg_validator_keeps_same_named_model_field` (:4420), `::test_single_base_model_arg_validator_unwraps_round_tripped_same_named_field` (:4439), `::test_positional_or_keyword_with_var_args` (:1489).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_build_schema _validate_single_arg single_arg_name positional_fields", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the flat-schema/wrap-validator split (wire flat, args wrapped) with the accepted-keys disambiguation ladder for any host that flattens single-model tools; adopt the pre-`*args` positional-fields rule verbatim. Adapt the eager-return-schema policy to your sandbox story. Omit nothing else. Coverage clean at the pinned commit.
