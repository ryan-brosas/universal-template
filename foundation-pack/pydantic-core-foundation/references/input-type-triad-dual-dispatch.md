<!-- capsule-v2 -->
# Input-type triad — how does one validator tree serve Python objects, parsed JSON, and string modes?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** What abstraction must a port reproduce so every validator is written once yet validates three input kinds with kind-correct errors?

## One `Input` trait + an `InputType` tag threaded through the whole tree
**Path/Symbol:** `src/input/input_abstract.rs:InputType` (:17-22), `Input<'py>` trait + convention doc (:54-57), `exact_int/exact_str` defaults (:96-112); consumed at `src/validators/mod.rs:_validate(..., InputType::Json, ...)` (:453-482).
**Signature:** `pub enum InputType { Python, Json, String }`; `fn validate_str(&self, strict: bool, coerce_numbers_to_str: bool) -> ValMatch<EitherString<'_, 'py>>` (one method per scalar/collection type).
**Data Shape:** Validators receive `&(impl Input<'py> + ?Sized)`; each request returns a backend-specific associated type (`Self::Dict<'a>: ValidatedDict<'py>`, `List`, `Tuple`, `Set`) so JSON gets `&JsonObject`/`&JsonArray`, Python gets Bound Py types, String mode gets StringMapping views.

### Decisive source
```rust
/// all types have three methods: `validate_*`, `strict_*`, `lax_*`
/// the convention is to either implement:
/// * `strict_*` & `lax_*` if they have different behavior
/// * or, `validate_*` and `strict_*` to just call `validate_*` if the behavior for strict and lax is the same
```

**Flow:** entrypoint picks InputType (validate_python→Python, validate_json funnel parses then →Json, validate_strings wraps in StringMapping →String, mod.rs:285-319) → `_validate` carries it on every call → validators ask for typed views via trait methods → errors render the interned kind name (`intern!(py,"json")` :29-36). Trait defaults `exact_int`/`exact_str` = strict validate then `require_exact()` else a plain IntType/StringType error — used where schema semantics demand exact scalars; backends may override (JsonValue::exact_str :188-193).
**Invariant:** No validator ever downcasts to a concrete input representation; kind-specific behavior lives ONLY in the Input impls. Error text embeds the active InputType, so a port must thread the kind even though it changes no validation logic.
**Probe:** executed live this pass: same `SchemaValidator(core_schema.list_schema(int_schema()))` accepts `[1,2]` / `b'[1,2]'` via validate_json and `[[1,2]]`-style python input via validate_python; `tests/conftest.py:PyAndJsonValidator.validate_test` (:76-88) runs every upstream test twice by json.dumps-ing inputs for the json arm.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "Input validate_str strict lax convention", limit: 10 });
// live: rank block led by src.input.input_abstract.Input.validate_* line-exact (:82-159)
```

## Verdict
Adopt the single-trait/three-implementations split plus the exactness-labeled ValidationMatch returns; adapt GATs to your language's generic mechanism; omit Rust lifetime erasure tricks (see borrow-input-collection-gats). Coverage: all cited paths no_recorded_issue @ gen 2026-08-25T20:09:30Z.
