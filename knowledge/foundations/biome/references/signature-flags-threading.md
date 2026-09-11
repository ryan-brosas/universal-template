<!-- capsule-v2 -->
# Signature-flags threading — how do `async`/`generator`/`constructor` bits flow from outer scopes into arrow parameters and bodies so `await`/`yield`/`super` legality is right without symbol tables?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Which flags enter `EnterFunction` vs `EnterParameters`, and why does an arrow's parameter list inherit the *enclosing* function's async/generator state while its body does not?

## SignatureFlags propagation rules
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:parse_function` (:206-226), `arrow_function_parameter_flags` (:835-848), `parse_arrow_body` (:934-979), `parse_function_id` (:338-373); flag defs in `crates/biome_js_parser/src/state.rs`.
**Signature:** `fn arrow_function_parameter_flags(p: &JsParser, mut flags: SignatureFlags) -> SignatureFlags`; state transitions via `EnterFunction(flags)` / `EnterParameters(flags)` (see js-parser-state.md).
**Data Shape:** Bitflags `{ASYNC, GENERATOR, CONSTRUCTOR, …}`; arrows carry a *derived* pair: own-declared ASYNC ∪ inherited parent context.

### Decisive source
```rust
fn arrow_function_parameter_flags(p: &JsParser, mut flags: SignatureFlags) -> SignatureFlags {
    if p.state().in_generator() {
        // Arrow functions inherit whatever yield is a valid identifier name from the parent.
        flags |= SignatureFlags::GENERATOR;
    }
    // The arrow function is in an async context if the outer function is in an async context or itself is declared async
    if p.state().in_async() {
        flags |= SignatureFlags::ASYNC;
    }
    flags
}
```
And the body side of `parse_arrow_body`: constructor bit re-attached (`if p.state().in_constructor() { flags |= CONSTRUCTOR }`) so nested `() => super()` still resolves; expression bodies parse inside `p.with_state(EnterFunction(flags), …)`, block bodies via `parse_function_body(p, flags)` which wraps `EnterFunction(flags)` around `parse_block_impl`.

**Flow:** declaration/expression parse sets ASYNC/GENERATOR from its own tokens → parameters enter with those flags → arrow derivation: parameter flags = own-declared + parent-state bits (because `x => x` has no header tokens to declare them) → body entry pushes the merged set again so inner statements see one consistent signature environment. Function *expressions* additionally push their own flags for the id binding (`function await(){}` legal in script mode); declarations leave id parsing under the parent's rules.
**Invariant:** The asymmetry is the point — arrow **parameters** need the enclosing function's `yield`-legality (the arrow may sit inside a generator's argument list), and its **body** needs the constructor bit for `super`. A porter who enters arrow scope with only self-declared flags breaks `(function*(){ () => (yield) })` style code. Flags are pushed per region via `with_state` (restored on exit) — never mutated globally.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/break_in_nested_function.js` (state reset across `EnterFunction`) plus `ok/async_arrow_expr.js` / `ok/arrow_in_constructor.js` (inheritance + super-in-arrow pins).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "arrow_function_parameter_flags EnterFunction EnterParameters SignatureFlags", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-entry-point model (parameters vs body get different derived flag sets); adapt bit names; omit Biome's exact mask values (owned by `js-parser-state.md`). This capsule owns the *propagation rules*, not the snapshot machinery.
