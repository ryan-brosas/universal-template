<!-- capsule-v2 -->
# allow_partial — how does "the tail may be truncated" survive both JSON parsing and collection validation?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `pydantic-core`. **Question:** What exact semantics must a port reproduce so streaming/partial inputs validate like upstream (`[[1,2],[3,` → `[(1,2)]`)?

## One-item lookahead marks the last element; its errors are dropped, earlier errors still raise
**Path/Symbol:** `src/validators/validation_state.rs:ValidationState.allow_partial` (:29-30), `enumerate_last_partial` (:90-92) + `EnumerateLastPartial` (:171-203); consumer `src/input/return_enums.rs:validate_iter_to_vec` (:120-164); parse side `src/validators/mod.rs:_validate_json` (jiter PartialMode, :468-471).
**Signature:** `fn enumerate_last_partial<I>(&self, iter: impl Iterator<Item = I>) -> impl Iterator<Item = (usize, bool, I)>`; `PartialMode::{Off, On, ...}` from jiter.
**Data Shape:** state flag is per-call; per-element truth is `(index, is_last_partial, item)`; `is_last = allow_partial.is_active() && next_item.is_none()`.

### Decisive source
```rust
for (index, is_last_partial, item_result) in state.enumerate_last_partial(iter) {
    state.allow_partial = match is_last_partial {
        true => allow_partial,
        false => PartialMode::Off,
    };
    ...
    Err(ValError::LineErrors(line_errors)) => {
        max_length_check.incr()?;
        if !is_last_partial {
            errors.extend(line_errors.into_iter().map(|err| err.with_outer_location(index)));
            if fail_fast { return Err(ValError::LineErrors(errors)); }
        }
    }
```

**Flow:** entrypoint passes allow_partial into jiter parsing (truncated text yields complete prefix values) AND into ValidationState; every collection validator (list/set/frozenset/dict via enumerate_last_partial callers: return_enums validate_iter_to_vec/set, dict.rs, list.rs, set.rs, frozenset.rs) flips the flag Off for non-last elements and leaves it active for the last; last-element LineErrors are silently discarded while earlier elements' errors still produce a full ValidationError. Structured types use `ValidatedDict::last_key` ("used in partial mode to check all errors occurred in the last value", input_abstract.rs:255-256).
**Invariant:** allow_partial is NOT JSON-only — it works over validate_python too (test_list asserts both). Non-last garbage always raises even under allow_partial. max-length accounting counts dropped-error items. Truncated-JSON success requires BOTH layers (jiter partial parse + error drop); either alone is insufficient.
**Probe:** executed live (P2): `v.validate_python([[1,2],'wrong'], allow_partial=True) == [(1,2)]`; `v.validate_python([[1,2],'wrong',[3,4]], allow_partial=True)` raises tuple_type; `v.validate_json(b'[[1, 2], [3,', allow_partial=True) == [(1,2)]`. Direct tests: `tests/validators/test_allow_partial.py:10-39` (list), `:88-113` (dict), `:127-193` (partial typed_dict); `tests/test_json.py:376-383` (from_json partial + EOF message, probe P3).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic-core", query: "enumerate_last_partial allow_partial is_last", limit: 8 });
// live rank-1: src.validators.validation_state.ValidationState.enumerate_last_partial (:90)
```

## Verdict
Adopt the lookahead-iterator + per-element flag-flip + last-error-drop triple verbatim; adapt jiter's PartialMode to your parser's incremental recovery; omit Rust iterator plumbing. Coverage: all cited paths no_recorded_issue @ gen 2026-08-25T20:09:30Z.
