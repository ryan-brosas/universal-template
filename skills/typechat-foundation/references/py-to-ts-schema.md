<!-- capsule-v2 -->
# Python→TypeScript schema compiler — how does a Python type become the TS prompt schema?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How is a TypedDict/dataclass/TypeAlias graph converted to TypeScript declarations, and what are the optionality and error-accumulation rules?

## Two-phase conversion pipeline
**Path/Symbol:** entry `python/src/typechat/_internal/ts_conversion/__init__.py:23-35` (`python_type_to_typescript_schema` → node conversion → string rendering); core `ts_conversion/python_type_to_ts_nodes.py:156-448` (`python_type_to_typescript_nodes`); AST dataclasses `ts_conversion/ts_type_nodes.py:1-78`; printer `ts_conversion/ts_node_to_string.py:21-97`.
**Signature:** `(py_type: type | TypeAliasType) -> TypeScriptSchemaConversionResult{typescript_schema_str, typescript_type_reference, errors}`.
**Data Shape:** worklists are OrderedDicts used AS ordered sets: `declared_types: OrderedDict[target, node|None]`, `undeclared_types` seeded with root; loop `while undeclared_types: py_type = undeclared_types.popitem()[0]` (:440-443) — LIFO discovery order, root LAST.

### Decisive source
```py
def declare_property(name, py_annotation, is_typeddict_attribute, optionality_default):
    current_annotation = py_annotation
    optional: bool | None = None
    while origin := get_origin(current_annotation):
        if origin is Annotated and comment is None:
            for metadata in current_annotation.__metadata__:
                if isinstance(metadata, Doc): comment = metadata.documentation; break
                if isinstance(metadata, str): comment = metadata; break
            current_annotation = current_annotation.__origin__
        elif origin is Required or origin is NotRequired:
            if not is_typeddict_attribute:
                errors.append(f"Optionality cannot be specified with {origin} outside of TypedDicts.")
            if optional is None: optional = origin is NotRequired
            else: errors.append(f"{origin} cannot be used within another optionality annotation.")
            current_annotation = get_args(current_annotation)[0]
        else:
            break
    if optional is None:
        optional = optionality_default
```
**Flow:** peel Annotated (harvesting Doc/str comments) + Required/NotRequired wrappers in one walk → convert remaining annotation via `convert_to_type_node` (str/int/float/bool/Any/object/None/Never/Self literals; list-family→`T[]` with Union elements promoted to `Array<T>`; dict→`Record<K,V>` with non-number keys coerced to string; tuple fixed vs `tuple[T, ...]`→array with ill-forms errored; Literal→union of JSON-stringified values) → discover referenced classes transitively → print.
**Invariant:** ERRORS ACCUMULATE — conversion never throws mid-graph; every failure appends prose to `errors[]` and substitutes `Any`. The translator constructor then raises ValueError listing all errors only if `_raise_on_schema_errors=True` (`translator.py:45-47`) — examples intentionally pass False to render schemas WITH error banners. Optionality defaults differ per container kind: TypedDict total=False ⇒ everything optional unless Required-wrapped; DATACLASSES invert — a field is optional IFF it has default/default_factory (`optional = not(field.default is MISSING and field.default_factory is MISSING)` :394). Name conflicts record an error but STILL emit duplicate interfaces (`reserve_name` :338-343).
**Probe:** `grep -c '__total__' python/src/typechat/_internal/ts_conversion/python_type_to_ts_nodes.py` (=2); `grep -c 'get_original_bases' ...python_type_to_ts_nodes.py` (=2 sites); live pin (executed this pass at the venv): Derived(A,B) of two locally-named C's yields `interface Derived extends C, C {}` plus TWO `interface C` blocks plus errors banner "Cannot create a schema using two types with the same name. C conflicts between ..." — byte-matching `tests/__py3.12_snapshots__/test_conflicting_names_1`.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"python_type_to_typescript_nodes declare_type TypedDict","limit":5}'
// single rank1 Function python/src/typechat/_internal/ts_conversion/python_type_to_ts_nodes.py 156-448
```

## Verdict
Adopt accumulate-don't-throw and both optionality defaults; adapt the node-dataclass layer if your host prints TS differently (keep precedence/parenthesization in the printer, not the converter); omit Protocol/dict special-bases filtering only if you never see TypedDict subclasses. Snapshot suites across py3.11–3.14 dirs are the direct tests.
