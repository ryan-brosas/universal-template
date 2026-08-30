<!-- capsule-v2 -->
# String-mode mapping duality — what IS an input under `validate_strings`?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** When a host exposes a "strings-only" validation mode, what data model must the input take, and which validator capabilities survive?

## StringMapping: a bare string OR a dict whose keys are strings and whose values are one more string-or-dict level
**Path/Symbol:** `src/input/input_string.rs:StringMapping` (:26-29) + `new_key`/`new_value` (:32-53) + `StringMappingDict` (:265-337).
**Signature:** `pub enum StringMapping<'py> { String(Bound<'py, PyString>), Mapping(Bound<'py, PyDict>) }`.
**Data Shape:** `new_key` downcasts to PyString else `string_type`; `new_value` tries PyString then PyDict else `string_type` — so nested values may descend exactly one more dict level, never list/set/tuple. `LocItem` conversion renders Mapping keys via `safe_repr` (:56-63).

### Decisive source
```rust
pub enum StringMapping<'py> {
    String(Bound<'py, PyString>),
    Mapping(Bound<'py, PyDict>),
}
// new_value: str -> String(..); dict -> Mapping(..); anything else -> StringType error
```

**Flow:** every scalar `Input::validate_*` splits on the variant: `String(s)` delegates to the shared always-converting parsers (`str_as_bool/int/float`, `create_decimal`, `bytes_as_date/time/datetime/timedelta`, `string_to_complex`) labeled `ValidationMatch::strict`; `Mapping(_)` returns the per-type type-error (:104-255). ALL collection views are the uninhabited `Never` with immediate type errors (:169-202) — string mode has no arrays. Function-validator args are impossible (`as_kwargs → None` :78-80; `validate_args`/`validate_args_v3` hard `ArgumentsType` "do we want to support this?"), but DATACLASS args work through `StringMappingDict` (:97-102). Dict iteration re-coerces each pair through `new_key`/`new_value` (:299-303); `last_key()` silently DROPS a non-string last key via `.ok()` (:330-336).
**Invariant:** string-mode input is a tree of depth ≤ 2 (string | dict of string→(string|dict)); any port that admits collections or non-string keys breaks the error taxonomy (everything degrades to `*_type` errors anchored on the whole input).
**Probe:** direct probe Q1 executed live against `_pydantic_core.abi3.so` 2.41.5 @ pin: `SchemaValidator(typed_dict{a:int,b:date}).validate_strings({'a':'1','b':'2017-01-01'})` → `{'a': 1, 'b': date(2017,1,1)}` (byte-matches tests/test_validate_strings.py::test_typed_dict :118-121); `validate_strings([1])` → `Input should be a valid string [type=string_type, input_value=[1], input_type=list]` (new_value's two-step downcast reports STRING_TYPE even for non-dict inputs); `SchemaValidator(list_schema(int)).validate_strings('x')` → `[type=list_type, input_value='x', input_type=str]`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "StringMapping string input backend mapping", limit: 10 });
// live run this pass: rank-1 = the Enum at src/input/input_string.rs:26-29; its validate_* methods occupy ranks 2+; py_get_string_mapping_item (lookup_key.rs:100-110) is the consumer side
```

## Verdict
Adopt the two-variant input model and strict-labeled shared-parser delegation for strings-only modes; adapt variant names/ownership to your host's value type; omit collection/function-arg support deliberately rather than half-porting it (upstream refuses args too). Coverage: input_string.rs no_recorded_issue @ gen 2026-08-25T20:09:30Z.
