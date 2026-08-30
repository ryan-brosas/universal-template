<!-- capsule-v2 -->
# Name registry build/load — how do you resolve serialized class names to constructors with customs overriding defaults, and errors that teach the caller?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How should a name→class registry behave for custom vs default types — validation order, override rules, and error messages that prescribe the fix?

## build_registry / load_from_registry contract
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_spec.py:build_registry` (:159-197) and `load_from_registry` (:200-236); evaluators call it via `dataset.py:_get_evaluator_registry/_load_evaluator_from_registry` (:1310-1349).
**Signature:** `build_registry(*, custom_types, defaults, get_name: Callable[[type[T]], str | None], label, validate=None) -> Mapping[str, type[T]]`; `load_from_registry(registry, spec, *, label, custom_types_param, context=None, instantiate=None) -> T`.
**Data Shape:** Registry maps serialization name → class. Names come from `get_serialization_name()` (defaults may return None to opt out).

### Decisive source
```python
for cls in custom_types:
    if validate is not None: validate(cls)
    name = get_name(cls)
    if name is None:
        raise ValueError(f'Custom {label} class {cls.__name__} has opted out of serialization (name is None)')
    if name in registry:
        raise ValueError(f'Duplicate {label} class name: {name!r}')
    registry[name] = cls
for cls in defaults:
    name = get_name(cls)
    if name is not None:
        # Allow overriding the defaults with custom types without raising an error
        registry.setdefault(name, cls)

# unknown name teaches the caller the whole surface + the exact kwarg
raise ValueError(
    f'{label.capitalize()} {name!r} is not in the provided `{custom_types_param}`. '
    f'Valid choices: {list(registry.keys())}. If you are trying to use a custom {label}, '
    f'you must include its type in the `{custom_types_param}` argument.')
# instantiation failure keeps the cause, adds context ('for dataset' / "for case 'text_case'")
raise ValueError(f'Failed to instantiate {label} {spec.name!r}{detail}: {e}') from e
```

**Flow:** Customs validated THEN registered (dupes raise); defaults fill gaps via setdefault — so a custom silently overrides a default of the same name, and a default opting out (None name) is skipped without error while a CUSTOM opt-out is loud. Load = lookup → enumerate-all-choices error prescribing `custom_types_param` → construct (`cls(*args, **kwargs)` or injected factory) → wrap any exception as ValueError with optional context suffix.
**Invariant:** Validation happens before registration for every custom type; defaults never raise. Error text must enumerate valid choices AND name the exact parameter that fixes it — the message is the API.
**Probe:** `tests/test_spec.py::TestBuildRegistry/TestLoadFromRegistry` (kernel-isolated, executed this pass); `tests/evals/test_dataset.py::test_duplicate_evaluator_failure` (:1204-1220) pins `"Duplicate evaluator class name: 'FirstEvaluator'"`; `test_from_text_failure` (:1141-1171) pins the full enumerated-choices message.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "build_registry load_from_registry", limit: 6 });
```
Live check this pass: BM25 search_graph located both functions rank 1-2 at `_spec.py :159-236` plus their direct test classes; coverage clean.

## Verdict
Adopt the kernel wholesale (validate-first customs, setdefault defaults, teaching errors). Adapt label nouns and the get_serialization_name hook. Omit NamedSpec short-form parsing — covered by named-spec-roundtrip.md; this capsule is the registry plane only.
