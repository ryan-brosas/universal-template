<!-- capsule-v2 -->
# Protected namespace conflict gate — when does a field name matching `model_` warn instead of raise?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** How does pydantic decide that an annotation colliding with `protected_namespaces` (default `('model_',)`) is fatal versus only warning?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_fields.py:_check_protected_namespaces` (:110-150), called per annotation from `collect_model_fields`.
**Signature:** `def _check_protected_namespaces(protected_namespaces: tuple[str | Pattern[str], ...], ann_name: str, bases: tuple[type[Any], ...], cls_name: str) -> None`.
**Data Shape:** Raises `ValueError` or emits a `UserWarning` (stacklevel=5); never returns a value. Supports string prefixes and compiled regex patterns side by side.

### Decisive source
```python
ns_violation = False
if isinstance(protected_namespace, Pattern):
    ns_violation = protected_namespace.match(ann_name) is not None
elif isinstance(protected_namespace, str):
    ns_violation = ann_name.startswith(protected_namespace)

if ns_violation:
    for b in bases:
        if hasattr(b, ann_name):
            if not (issubclass(b, BaseModel) and ann_name in getattr(b, '__pydantic_fields__', {})):
                raise ValueError(
                    f'Field {ann_name!r} conflicts with member {getattr(b, ann_name)}'
                    f' of protected namespace {protected_namespace!r}.'
                )
    else:
        # no base conflict: build a suggestion list of the NON-conflicting namespaces and WARN
        valid_namespaces: list[str] = []
        for pn in protected_namespaces:
            ...
        warnings.warn(
            f'Field {ann_name!r} in {cls_name!r} conflicts with protected namespace {protected_namespace!r}.\n\n'
            f"You may be able to solve this by setting the 'protected_namespaces' configuration to {valid_namespaces_str}.",
            UserWarning, stacklevel=5,
        )
```

**Flow:** test each configured namespace against the annotation (regex `.match` or `str.startswith`) → on violation, scan bases: if some base has the name AND it is not already a parent's model field, this is shadowing a real member ⇒ hard `ValueError`; otherwise emit a warning whose message suggests replacement namespaces (the non-matching ones, rendered as `re.compile(...)` or `'prefix'`).
**Invariant:** Inheriting/overriding a field that already exists in a parent's `__pydantic_fields__` stays legal even under its namespace; only conflicts with non-field members escalate to errors. The warning doubles as config advice (`protected_namespaces=()` escape hatch).
**Probe:** `tests/test_main.py::test_protected_namespace_default` (:3064-3070, default `'model_dump'` warning), `test_custom_protected_namespace` (:3073-3082), `test_multiple_protected_namespace` (:3085-3098 — pins the suggestion rendering `('protect_me_', re.compile('re_protect'))`), `test_protected_namespace_pattern` (:3101-3107).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "_check_protected_namespaces protected namespace field conflict", limit: 10, fields: ["signature", "lines"] });
```

## Verdict
Adopt the warn-vs-raise split keyed on whether the collided base member is itself an inherited model field, plus mixed str/Pattern namespace support. Adapt the suggestion-message rendering to your host's error style. Omit the stacklevel arithmetic if you don't mirror Python warnings semantics.
