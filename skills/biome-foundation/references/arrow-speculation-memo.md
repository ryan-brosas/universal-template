<!-- capsule-v2 -->
# Speculative arrow-head rewind — how do you try an ambiguous arrow parse and cheaply remember the failure so the position is never re-tried?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the exact protocol for speculative arrow-function parsing — which checks gate the attempt, what rewinds on failure, and how is the negative result cached?

## try_parse_parenthesized_arrow_function_head + not_parenthesized_arrow memo
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:try_parse_parenthesized_arrow_function_head` (:551-610), `parse_possible_parenthesized_arrow_function_expression` (:615-645).
**Signature:** `fn try_parse_parenthesized_arrow_function_head(p: &mut JsParser, ambiguity: Ambiguity) -> Result<(Marker, SignatureFlags), Marker>` with `Ambiguity::{Allowed, Disallowed}`.
**Data Shape:** `Ok((m, flags))` = caller must complete marker `m`; `Err(m)` = caller abandons `m` — safe only because `try_parse` rewinds the whole parser when the closure returns `Err`. Failure memo: `state.not_parenthesized_arrow: FxHashSet<TextSize>` of start positions.

### Decisive source
```rust
if p.state().not_parenthesized_arrow.contains(&start_pos) {
    return Absent; // already tried here and failed — never re-attempt
}
match try_parse(p, |p| {
    try_parse_parenthesized_arrow_function_head(p, Ambiguity::Disallowed)
}) {
    Ok((m, flags)) => { /* parse body; complete JS_ARROW_FUNCTION_EXPRESSION */ }
    Err(m) => {
        // SAFETY: Abandoning the marker here is safe because `try_parse` rewinds if
        // the callback returns `Err`
        m.abandon(p);
        p.state_mut().not_parenthesized_arrow.insert(start_pos);
        Absent
    }
}
```
Inside the head (each `Err(m)` return is a bail-out point): eat `async` → optional TS type params; under `Disallowed`, bail unless the type-param list ended exactly at `>` (`p.last() == Some(T![>])`) → bail if next isn't `(` → parameter list → bail if last token wasn't `)` → TS return type → line-terminator-before-arrow error → expect `=>`.

**Flow:** classifier says `Unknown` ⇒ speculative attempt with `Ambiguity::Disallowed`; every "expected char missing" check returns `Err(marker)` instead of emitting diagnostics; `try_parse` checkpoints + rewinds; failed start position is memoized so later re-entry from the same expression position skips straight to parenthesized-expression parsing. `Ambiguity::Allowed` (classifier already said True) parses the same head but tolerates missing pieces, producing error nodes instead of bailing.
**Invariant:** The Err path must never emit parser events or diagnostics that survive the rewind — all ambiguity decisions happen as pure bail-outs. Memoization is keyed by *start position*, inserted exactly once per failed speculation. A porter who emits errors inside the Disallowed head, or who forgets the memo, re-parses `(a)` as an arrow candidate after every expression-level retry.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/arrow_expr_in_alternate.js` (`a ? (b) : a => {};` — the `(b)` in alternate position stays a paren expr) and `error/ts_function_overload.ts`-style `<string>(test)` cast cases cited in the head's doc comment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "try_parse not_parenthesized_arrow Ambiguity arrow head", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the speculate→rewind→memoize-negative trio for any ambiguous construct; adapt `Ambiguity` to a host-side two-mode enum; omit the specific token checks (they are grammar surface). Distinct from `arrow-disambiguation.md` (the True/False/Unknown classifier): this capsule is the *execution protocol* after Unknown.
