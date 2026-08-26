<!-- capsule-v2 -->
# ValidationState — what thread-through context exists, and how do scoped mutations restore themselves?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** Which mutable knobs flow through validation, and what is the correct pattern for temporarily changing them mid-tree?

## Extra is readonly behind accessors; everything mutable rides ValidationState with RAII scopes
**Path/Symbol:** `src/validators/validation_state.rs:ValidationState` (:21-138); `Extra` lives in `src/validators/mod.rs:670-741`.
**Signature:** `rebind_extra(f: impl FnOnce(&mut Extra)) -> ValidationStateWithReboundExtra`; `scoped_set(projector, new_value) -> ScopedSetState`; `floor_exactness(exactness)`; `strict_or(default)/extra_behavior_or(default)/validate_by_alias_or(default)/validate_by_name_or(default)`.
**Data Shape:** `ValidationState { recursion_guard: &mut RecursionState, exactness: Option<Exactness>, fields_set_count: Option<usize>, allow_partial: PartialMode, has_field_error: bool, extra: Extra<'a,'py> }`. `Exactness { Lax < Strict < Exact }` derives Ord (:14-19). `Extra` carries input_type (Python|Json|String), data (accumulated model dict for validator/data kwargs), strict, extra_behavior, from_attributes, context, field_name, self_instance, cache_str, by_alias, by_name.

### Decisive source
```rust
pub fn scoped_set<'state, P, T>(&'state mut self, projector: P, new_value: T)
    -> ScopedSetState<'state, 'a, 'py, P, T>
{
    let value = std::mem::replace((projector)(self), new_value);
    ScopedSetState { state: self, projector, value }
}
impl Drop for ScopedSetState<'_, '_, '_, P, T> {
    fn drop(&mut self) { std::mem::swap((self.projector)(self.state), &mut self.value); }
}
```

**Flow:** Callers compose scopes: e.g. model-fields wraps its field loop in `state.rebind_extra(|extra| extra.data = Some(model_dict.clone()))` then `scoped_set(|s| &mut s.has_field_error, false)` (model_fields.rs :181-182), and per-field rebinds `extra.field_name` (:199). Union smart mode saves/restores `exactness`+`fields_set_count` by hand around each choice trial (union.rs :109-171) because they are METRICS, not config. `floor_exactness` lowers the ambient floor monotonically (Exact→anything, Strict→Lax allowed; Lax never raised) so outer unions observe the true best quality achieved (:115-125).
**Invariant:** Never mutate `Extra` fields directly outside a rebound scope — borrow checker enforces readonly-ness by construction (`extra` private, `extra()` returns `&_`). Defaults resolution ladder is always `call-site override → validator-schema setting → global default` (the `_or` helpers encode exactly that three-step).
**Probe:** `grep -n 'pub fn scoped_set' src/validators/validation_state.rs` =1 at :70; `grep -n 'fn floor_exactness' src/validators/validation_state.rs` =1 at :115; direct behavior: tests/validators/test_union.py smart-mode suite passes at pin (83 passed this pass).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "ValidationState floor_exactness rebind_extra", limit: 4 });
// live rank-1: ValidationState.floor_exactness :115-125 line-exact
```

## Verdict
Adopt: single state object, readonly-context-with-scoped-rebind (drop-guard restore), monotone exactness floor, three-layer defaults. Adapt field set to your feature surface (keep `has_field_error` semantics — it gates data-dependent default factories). Omit the generic-projector typing trick if your language lacks HKTs; a simple save/set/restore closure suffices.
