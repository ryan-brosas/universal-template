<!-- capsule-v2 -->
# Inheritance flattening — when do base TypedDict/dataclass members re-declare vs inherit?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** Which attributes does the schema printer re-declare on a derived interface, and which become `extends` references?

## Base filtering + identical-hint suppression
**Path/Symbol:** `python/src/typechat/_internal/ts_conversion/python_type_to_ts_nodes.py:118-127` (`_KNOWN_SPECIAL_BASES`), `:364-373` (base collection), `:420-425` (`attribute_identical_in_all_bases`).
**Signature:** `raw_but_filtered_bases = [base for base in get_original_bases(py_type) if not(base is object or base in _KNOWN_SPECIAL_BASES or get_origin(base) in _KNOWN_GENERIC_SPECIAL_FORMS)]`.
**Data Shape:** `_KNOWN_SPECIAL_BASES = {typing.TypedDict, typing_extensions.TypedDict, Protocol, dict}` — dict is included because older Pythons lack `__orig_bases__` on typing-TypedDicts, so get_original_bases falls back to `__bases__` mapping straight to dict.

### Decisive source
```py
base_attributes: OrderedDict[str, set[object]] = OrderedDict()
for base in raw_but_filtered_bases:
    for prop, type_hint in get_type_hints(get_origin(base) or base, include_extras=True).items():
        base_attributes.setdefault(prop, set()).add(type_hint)

def attribute_identical_in_all_bases(attr_name, type_hint, base_attributes):
    return attr_name in base_attributes and len(base_attributes[attr_name]) == 1 and type_hint in base_attributes[attr_name]
```
**Flow:** for TypedDicts: every own attribute whose hint is NOT identical-in-all-bases becomes a re-declared property; hints identical across ALL bases are dropped from the body and carried by `extends`. Dataclasses skip this filter entirely — all `__dataclass_fields__` re-declare (:392-396).
**Invariant:** identity is by annotation OBJECT equality (`type_hint in set`) not string form — two structurally identical but distinct aliases still re-declare. The multi-base same-name case is exactly the test_conflicting_names_1 fixture: Derived(A,B) with different member names keeps BOTH properties (`my_attr_1`, `my_attr_2` in the snapshot) while emitting the name-conflict error. Generic bases resolve through `get_origin(base)` before hint extraction.
**Probe:** live-executed this pass at /tmp/tc-p1-run venv (script inline via python -c): Derived prints `my_attr_1: string;\n    my_attr_2: number;` inside interface Derived with extends C, C — matches py3.12 snapshot byte-for-byte modulo module path in the error text. Static pin: `grep -c 'attribute_identical_in_all_bases' .../python_type_to_ts_nodes.py` (=2 def+call).
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"get_original_bases TypedDict inheritance","limit":3}'
// (BM25 may rank the whole converter function; the seam lives at :364-373/:420-425 of python_type_to_ts_nodes.py)
```

## Verdict
Adopt the identical-hint suppression to keep schemas compact AND the explicit special-bases list so typing-era quirks don't leak `dict` into extends; adapt if your host emits interfaces differently; omit dataclass re-declaration parity only if your dataclasses never subclass user types.
