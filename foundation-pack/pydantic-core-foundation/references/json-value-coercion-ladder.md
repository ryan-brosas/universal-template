<!-- capsule-v2 -->
# JsonValue coercion ladders — which JSON scalars convert, with what exactness label?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** When validating a parsed JsonValue, exactly which coercions fire in strict vs lax mode and which exactness does each carry?

## Str is "converting" not exact; arrays back tuple/set/frozenset strict-never-exact
**Path/Symbol:** `src/input/input_json.rs:impl Input<'py> for JsonValue<'data>` (:47-392) — validate_str :128-145, validate_bytes :147-159, validate_bool :161-175, validate_int :177-186, exact_str override :188-193, validate_float :195-206, validate_decimal :208-218, dict/list/tuple/set/frozenset :220-280, temporals :302-367.
**Signature:** each returns `ValResult<ValidationMatch<T>>` where ValidationMatch carries Exact/Strict/Lax (feeds union ranking + floor_exactness).
**Data Shape:** JsonValue::{Null,Bool,Int(i64),BigInt,Float,Str,Array,Object}; BigInt exists because jiter defers over-range ints.

### Decisive source
```rust
// Justification for `strict` instead of `exact` is that in JSON strings can also
// represent other datatypes such as UUID and date more exactly, so string is a
// converting input
match self {
    JsonValue::Str(s) => Ok(ValidationMatch::strict(s.as_ref().into())),
    JsonValue::Int(i) if !strict && coerce_numbers_to_str => Ok(ValidationMatch::lax(i.to_string().into())),
    ...
}
```

**Flow:** bool: Bool exact; Str/Int/Float lax via str_as_bool/int_as_bool/float_as_int chain. int: Int/BigInt exact; Bool→0/1 lax; Float→float_as_int lax (fractional → int_from_float error); Str→str_as_int lax. float: Int→F64 **strict-not-exact** (:198); BigInt via `b.to_f64().expect(...)` (:199-201); Bool/Str lax. decimal: Float goes string-mediated (`f.to_string()` → PyString → create_decimal); Str/Int/BigInt direct; `_strict` ignored (:208). date/time/datetime/timedelta: only Str parses bytes (speedate), marked **strict**; Int/Float lax numerics; BigInt time → explicit TimeParsing TimeTooLarge error (:319-329). tuple/set/frozenset: Array serves all three as **strict never exact**, commented "otherwise it would be impossible to create a set from JSON" (:254, :267).
**Invariant:** Exactness labels are semantic promises consumed by smart-union ranking — changing any label changes union winners. coerce_numbers_to_str gates ALL number→string conversion. JSON has no bytes type: validate_bytes only reinterprets Str via `mode.deserialize_string` (Utf8/Base64 config ladder).
**Probe:** executed live at pin (tests/test_json.py:71-111 parametrize shapes): `'123'`/`'123.0'`→123 int; `'123.4'` → int_from_float; `'"string"'` → int_parsing; float from `'123'` → 123.0. P7: `'Infinity'` parses when allow_inf_nan.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "JsonValue validate_int validate_float BigInt expect", limit: 8 });
// live: rank block led by src.input.input_json.JsonValue.validate_* line-exact
```

## Verdict
Adopt the per-type ladder table WITH its exactness column verbatim; adapt speedate/jiter specifics; omit the Rust Either enums. Caveat: the second positional arg of parse_with_config (`true`) is unconfirmed from repo sources (jiter crate not vendored here). Coverage: input_json.rs no_recorded_issue @ gen 2026-08-25T20:09:30Z.
