<!-- capsule-v2 -->
# Member/call chain parsing — how do `?.`, TS type arguments, and tagged templates interleave in one postfix loop?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does one loop own `.`, `[`, `?.`, `<T>()`, template tags, and non-null assertions without mis-nesting any of them?

## parse_member_expression_rest + parse_call_expression_rest
**Path/Symbol:** `crates/biome_js_parser/src/syntax/expr.rs:parse_member_expression_rest` (:714-807), `parse_call_expression_rest` (:1752-1830).
**Signature:** `fn parse_member_expression_rest(p, lhs: CompletedMarker, context, allow_optional_chain: bool, in_optional_chain: &mut bool) -> CompletedMarker`
**Data Shape:** Loop state: the accumulated `CompletedMarker`, an `in_optional_chain` out-flag threaded across both loops, and a `ParserProgress` guard. Marker surgery: `precede`, `undo_completion`, and — critically — `lhs.clone().precede(p)` before speculative type-argument parsing.

### Decisive source
```rust
// Cloning here is necessary because parsing out the type arguments may rewind in which
// case we want to return the `lhs`.
let m = match lhs.kind(p) {
    TS_INSTANTIATION_EXPRESSION if !p.at(T![?.]) => lhs.clone().undo_completion(p),
    _ => lhs.clone().precede(p),
};
let start_pos = p.source().position();
// ... parse_ts_type_arguments_in_expression may rewind ...
} else {
    // Safety: ... if the parser is at '<': `parse_ts_type_arguments_in_expression` rewinds
    // if what follows aren't valid type arguments and this is the only way we can reach this branch
    debug_assert_eq!(p.source().position(), start_pos);
    m.abandon(p);
    lhs
};
```

**Flow:** member loop handles `.` / `[` / `?.[|name|template]` / `!` (line-break-gated) / BACKTICK (undoing a just-completed instantiation expression for `f<T>\`\`` ) / `<<`-style type arguments → call loop re-enters it after every `(...)`/type-argument group so chains like `a<T>(x)(y)[z]?.w` nest correctly → optional-chain flag propagates so a later tagged template becomes `JS_BOGUS_EXPRESSION`.
**Invariant:** The CompletedMarker must be *cloned* before speculative type-argument parsing because markers are indices into the event stream — completing/abandoning consumes them. `TS_INSTANTIATION_EXPRESSION` followed by property access is an error (`f<b>.c`) but `f<b>?.()` is legal; the undo-vs-precede choice encodes that. JSX gets a special break: `a </test/` with no trivia between `<` and `/` stops the chain so the regex isn't eaten as less-than.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts/ts_call_expr_with_type_arguments.ts` (`(() => a)<A, B, C>();`) and `error/ts/optional_chain_call_without_arguments.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_member_expression_rest parse_call_expression_rest optional", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-loop chain walker with cloned-marker speculation; adapt operator sets; omit TS instantiation/JSX arms when porting to languages without them. A porter who drops the clone will corrupt the event stream on the first rewind inside a chain.
