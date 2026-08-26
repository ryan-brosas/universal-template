<!-- capsule-v2 -->
# from_spec template resolution — hint-directed TypeAdapter validation of only TemplateStr-bearing parameters

## Source / Question
`pydantic_ai_slim/pydantic_ai/_template.py` @ `main@b3cdbc96` (MIT); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** Declarative capability specs accept strings that MAY be templates (`'Hello {{name}}'`) — how do you compile exactly the parameters whose declared type accepts `TemplateStr`, leaving plain `str` params untouched, without each spec author writing validation boilerplate? A porter will convert every string arg (corrupting literal-brace content) or none (breaking templated specs).

## Path / Symbol
`_template.py` — `validate_from_spec_args` (:14–54), `_hint_contains_template_str` (:57–64); consumer: `capabilities/abstract.py` `from_spec` machinery; template engine: `template.py::TemplateStr`.

## Signature
```python
def validate_from_spec_args(cls, args: tuple, kwargs: dict,
    validation_context: dict[str, Any]) -> tuple[tuple, dict]
def _hint_contains_template_str(hint: Any) -> bool   # recursive through get_args
```

## Data Shape
Validation context carries `deps_type`/`deps_schema` so `TemplateStr.__get_pydantic_core_schema__` can compile `{{...}}` placeholders against deps. The function is a pydantic model-validator on the spec base class: it receives raw `(args, kwargs)` and returns possibly-replaced copies.

### Decisive source — hint gate before any work (:28–52)
```python
try:
    hints = get_function_type_hints(cls.from_spec)
except Exception:
    return args, kwargs          # unresolvable hints = leave everything alone
hints.pop('return', None)
if not any(_hint_contains_template_str(h) for h in hints.values()):
    return args, kwargs          # fast path: no TemplateStr anywhere = noop
sig = inspect.signature(cls.from_spec)
params = [p for p in sig.parameters.values() if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)]
for i, param in enumerate(params):
    hint = hints.get(param.name)
    if hint is None or not _hint_contains_template_str(hint):
        continue                 # plain-str params keep their raw string verbatim
    ta = TypeAdapter(hint)
    if i < len(args):
        new_args[i] = ta.validate_python(args[i], context=validation_context)
    elif param.name in kwargs:
        new_kwargs[param.name] = ta.validate_python(kwargs[param.name], context=validation_context)
```
`TemplateStr.__get_pydantic_core_schema__` auto-compiles strings containing `{{` into TemplateStr instances during `validate_python`; plain strings pass through as `str`.

**Flow:** spec load → validator inspects from_spec hints ONCE → if no parameter accepts TemplateStr, zero-cost passthrough → else per-parameter TypeAdapter with the shared deps context → positional index OR kwarg name addressed, never both.

**Invariant:** Conversion is type-DIRECTED (declared hint decides), not content-directed (a `'{{x}}'` string into a `str` param stays literal); failures resolving hints degrade to noop rather than breaking spec loads.

**Probe:** `tests/test_template.py::TestValidateFromSpecArgs::test_resolves_template_in_positional_arg` (:142), `test_resolves_template_in_keyword_arg` (:148), `test_plain_string_unchanged` (:153), `test_no_template_str_in_hints_is_noop` (:160 — `'Hello {{name}}'` into a `str` param stays a plain str); end-to-end from_spec cases :177–209.

## Get live surrounding code
**Retrieve:**
```
search_graph --project mnt-hdd-utopia-inspo-pydantic-ai --query 'validate_from_spec_args _hint_contains_template_str TypeAdapter'
```

## Verdict
**Adopt** the hint-gated, per-parameter, context-carrying validation ladder for any declarative-spec surface with optional templating. **Adapt** where hints/context come from. **Omit** the TemplateStr rendering internals (separate template-engine concern).
