<!-- capsule-v2 -->
# Recursion guard — how are cyclic INPUTS detected without segfaults, and what limits exist?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What identifies a recursion cycle, what error surfaces, and how is depth bounded per platform?

## Two-key identity set (input-object id × validator node id) + platform-tuned u8 depth ceiling
**Path/Symbol:** `src/recursion_guard.rs:RecursionGuard/RecursionState/RECURSION_GUARD_LIMIT/RecursionStack` (whole file, 217L); used from `src/validators/definitions.rs` (DefinitionRefValidator) and serializer state (`SerializationState::recursion_guard`).
**Signature:** `RecursionGuard::new(state, obj_id: usize, node_id: usize) -> Result<Self, RecursionError::{Cyclic, Depth}>`; Drop impl releases BOTH registrations.
**Data Shape:** `RecursionState { ids: RecursionStack, depth: u8 }`; key = `(id-of-input-object, id-of-validator-node)` — obj ids alone are insufficient (same dict may legally appear twice as siblings), node ids alone likewise.

### Decisive source
```rust
pub fn new(state: &mut S, obj_id: usize, node_id: usize) -> Result<RecursionGuard<'_, S>, RecursionError> {
    state.access_recursion_state(|state| {
        if !state.insert(obj_id, node_id) { return Err(RecursionError::Cyclic); }
        if state.incr_depth() { return Err(RecursionError::Depth); }
        Ok(())
    })?;
    Ok(RecursionGuard { state, obj_id, node_id })
}
pub const RECURSION_GUARD_LIMIT: u8 = (if cfg!(any(target_family="wasm", all(windows, PyPy))) { 49 }
    else if cfg!(any(PyPy, windows)) { 99 } else { 255 }) - GUARD_OFFSET; // GUARD_OFFSET=20 under debug_assertions
```

**Flow:** Only re-entrant nodes (definition refs, infer serializers) take guards. Insert fails ⇒ Cyclic ⇒ validators surface `ErrorType::RecursiveLoop` ("Recursion error - cyclic reference detected"); depth overflow ⇒ Depth (backup against identity-check misses, issue #143). Stack container starts as a 16-slot inline `[MaybeUninit; 16]` array with linear scan and PROMOTES once to an AHashSet at capacity (ARRAY_SIZE=16, :134-187) — remove asserts LIFO pairing ("remove did not match insert"). Release builds use checked_add against 255 (never overflows before limit check); debug/special targets saturate.
**Invariant:** Guard must be held for the duration of sub-validation — RAII drop decrements depth AND removes the exact key; non-LIFO removal panics in debug (array path). Exposed to Python as `_pydantic_core._recursion_limit`.
**Probe:** `grep -n 'pub const RECURSION_GUARD_LIMIT' src/recursion_guard.rs` =1 (:78); `grep -n 'const ARRAY_SIZE' src/recursion_guard.rs` → `134:...16`; direct tests: test_cyclic_data :892 + test_cyclic_data_threeway :934 in tests/validators/test_definitions_recursive.py assert EXACT error payloads `{'type':'recursion_loop','loc':('b','a'),'msg':'Recursion error - cyclic reference detected'}` — green this pass; depth-limit families in tests/benchmarks/test_micro_benchmarks.py :281/:1348 walk `_recursion_limit`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "RecursionGuard new drop cyclic depth", limit: 4 });
// live rank-1..3 line-exact: RecursionGuard.drop :52-57, .new :32-43, incr_depth :112-121
```

## Verdict
Adopt: two-key identity cycle detection with RAII release, platform-tuned hard depth limit, small-array→set promotion. Adapt key derivation (needs stable object identity + stable validator identity). Omit wasm/PyPy branches unless you target them; keep SOME hard cap regardless — identity checks alone have missed cycles historically (#143).
