<!-- capsule-v2 -->
# GenericPyMapping tri-dispatch — how do dict / Mapping / from-attributes inputs share one field-lookup path, and what does `last_key` do when it can't?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** How should a port unify plain dicts, arbitrary mappings, and attribute-bearing objects behind one lookup interface without letting worst-case backends corrupt error/extra semantics?

## Three variants chosen at view-construction; `last_key` degrades SILENTLY to None per variant
**Path/Symbol:** `src/input/input_python.rs:GenericPyMapping` (:845-849), construction ladder (:392-444), consumer impl (:851-902); accessors `LookupKey::py_get_dict_item/py_get_mapping_item` (`src/lookup_key.rs:89-121`).
**Signature:** `pub enum GenericPyMapping<'a,'py> { Dict(&'a Bound<PyDict>), Mapping(&'a Bound<PyMapping>), GetAttr(Bound<PyAny>, Option<Bound<PyDict>>) }`.
**Data Shape:** keys/items stay `Bound<'py, PyAny>` (unlike StringMapping's pre-coerced variants); the GetAttr variant carries an optional kwargs dict extracted from a `(obj, kwargs)` pair.

### Decisive source
```rust
fn last_key(&self) -> Option<Self::Key<'_>> {
    match self {
        Self::Dict(dict) => dict.keys().iter().last(),
        // see https://github.com/pydantic/pydantic-core/pull/1512#discussion_r1826057970
        Self::Mapping(mapping) => mapping.call_method0(intern!(mapping.py(), "keys"))
            .ok()?.try_iter().ok()?.last()?.ok(),
        Self::GetAttr(_, _) => None,
    }
}
```

**Flow:** construction decides everything downstream: `strict_dict` accepts exact dicts only (subclass-of-dict falls to `Mapping(self.downcast::<PyMapping>()?)`, else dict_type :397-405); `lax_dict` admits any PyMapping (:407-415); `validate_model_fields(from_attributes)` walks dict → mapping (LAX ONLY, gated `!strict`) → `from_attributes_applicable` GetAttr → `(obj, kwargs)` pair (:417-443). Lookup then dispatches per variant to `py_get_dict_item` / `py_get_mapping_item` / `py_get_attr` (:862-871); `is_py_get_attr()` is the marker other validators use to detect attribute-sourced fields. `last_key` (used for extra-key reporting and duplicate-key errors) must NEVER raise on exotic mappings: each hop is `.ok()?`-swallowed, returning None so callers fall back to non-keyed errors.
**Invariant:** view construction may raise type errors; CONSUMPTION of an already-constructed view must be total — a hostile `keys()` implementation degrades to `last_key() == None`, never to a Python exception escaping mid-validation. A port that propagates mapping-method errors here turns user input into internal crashes.
**Probe:** direct probe Q3 executed live @ pin: `SchemaValidator(typed_dict{f:int}).validate_python(MappingProxyType({'f':'1'}))` → `{'f': 1}` via the Mapping arm; model-schema variant `validate_python(Source(), from_attributes=True)` with Source a foreign class carrying class-attr `f='42'` → fresh `Model` instance `{'f': 42, '__pydantic_extra__': None, '__pydantic_private__': None, '__pydantic_fields_set__': {'f'}}` via GetAttr; non-mapping input keeps `[type=model_type]`. Side observation feeding the revalidate capsule: an EXACT instance of the model class itself comes back untouched under default Revalidate::Never. (Byte-parity rows in tests/validators/test_dict.py::test_mapping :107-125 read directly this pass.)
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "GenericPyMapping last_key mapping get_attr dispatch", limit: 10 });
// live run this pass: Enum at input_python.rs:845-849 rank-1; iterate/get_item/last_key/is_py_get_attr methods follow; py_get_string_mapping_item surfaces as the string-mode sibling accessor
```

## Verdict
Adopt construct-time variant selection + total (never-raising) consumption contract for third-party mappings; adapt which host types map to Dict vs Mapping vs GetAttr; omit the `(obj, kwargs)` extraction if your host lacks an args-tuple concept. Caveat: `last_key` silent-None behavior has no dedicated upstream test — source excerpt (incl. PR #1512 review link) is the contract. Coverage: input_python.rs, lookup_key.rs no_recorded_issue @ gen 2026-08-25T20:09:30Z.
