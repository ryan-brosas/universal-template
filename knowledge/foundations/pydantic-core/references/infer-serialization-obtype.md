<!-- capsule-v2 -->
# Inference serialization — how does schema-less serialization dispatch, and what happens on recursion per mode?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** How are unknown Python objects classified and converted in both python and json modes — including the cyclic case?

## ObType classification drives one match with TWO mode arms; python-mode recursion returns the value AS-IS
**Path/Symbol:** `src/serializers/infer.rs:infer_to_python/infer_to_python_known/infer_serialize` (:32-181+); `ObType` catalog in `src/serializers/ob_type.rs`.
**Signature:** `infer_to_python(value, state)` → `ob_type_lookup.get_type(value)` classification → `infer_to_python_known(ob_type, value, state)`.
**Data Shape:** ObType spans exact types (None/Bool/Int/Str), subclass variants (IntSubclass/FloatSubclass/StrSubclass), containers, temporals, Url/Path/IP/UUID, dataclasses/generators/enums.

### Decisive source
```rust
let mut guard = match state.recursion_guard(value, INFER_DEF_REF_ID) {
    Ok(v) => v,
    Err(e) => return match mode {
        SerMode::Json => Err(e),
        // if recursion is detected by we're serializing to python, we just return the value
        _ => Ok(value.clone().unbind()),
    },
};
```

**Flow:** JSON arm upcasts subclasses to base types (IntSubclass re-extracts; StrSubclass re-strings) because json output must be plain; NaN/Infinity become strings "NaN"/"Infinity" (or null under InfNanMode::Null); bytes go through BytesMode; tuples serialize as ARRAYS via filter-walked seq. Python arm preserves richer shapes (sets stay sets, etc.). Recursion guard uses a sentinel id INFER_DEF_REF_ID=usize::MAX distinct from definition-ref slots; on cycle: Json raises PydanticSerializationError, Python silently emits the shared object reference (cycles are legal in memory). Keys recurse through `infer_json_key` separately from values.
**Invariant:** Classification happens ONCE per value then dispatches — never isinstance-chains interleaved with conversion. Subclass upcasting is explicit per-variant, not blanket.
**Probe:** `grep -n 'INFER_DEF_REF_ID' src/serializers/infer.rs` =2 (:41 const, :51 use); direct tests: tests/serializers/test_any.py green this pass (166 batch; its :384 walks `_recursion_limit`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "infer_to_python_known ObType SerMode recursion", limit: 4 });
// live rank-family: infer.rs functions resolve line-exact
```

## Verdict
Adopt: classify-then-dispatch with per-mode arms, subclass upcast discipline, divergent recursion policy (raise-in-json vs return-as-is-in-python). Adapt ObType to your type lattice. Omit dataclass/generator inference arms if you forbid schema-less serialization of those.
