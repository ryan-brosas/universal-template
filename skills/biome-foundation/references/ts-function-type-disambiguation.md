<!-- capsule-v2 -->
# Function-type vs parenthesized-type disambiguation — with one-token lookahead and a diagnostic-silent parameter probe, how does `(a: string) => T` become a function type while `(string)` stays parenthesized?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the type parser decide between `TS_FUNCTION_TYPE` and `TS_PARENTHESIZED_TYPE` at `(` without unbounded lookahead or stray diagnostics?

## is_at_function_type lookahead
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:is_at_function_type` (:1761-1793), `parse_ts_function_type` (:1808-1827).
**Signature:** `fn is_at_function_type(p: &mut JsParser) -> bool` — `p.at(<)` ⇒ true immediately; else requires `(` + one `p.lookahead(…)`.
**Data Shape:** Lookahead consumes `(` then tries `skip_parameter_start(p)` (the *diagnostic-silent* binding probe from function.rs — a destructuring pattern counts as started only if `diagnostics().len()` didn't grow).

### Decisive source
```rust
p.lookahead(|p| {
    p.bump(T!['(']);
    if p.at(T![')']) || p.at(T![...]) {
        // () not a valid parenthesized type
        // (... rest parameters are only valid in function types
        return true;
    }
    if skip_parameter_start(p) {
        if p.at_ts(token_set![T![:], T![=], T![,], T![?]]) {
            return true;   // parameter-ish follower: annotation/default/comma/optional
        }
        return p.at(T![')']) && p.nth_at(1, T![=>]);  // (a) => …
    }
    false
})
```

**Flow:** dispatch order in `parse_ts_type`: constructor type first (`new`/`abstract new`), then function type via this predicate, else union ladder. Positive ⇒ `parse_ts_function_type` parses `<params>` (const allowed), `ParameterContext::Declaration`, return type with conditionals re-enabled.
**Invariant:** The predicate's follower set is exactly what cannot occur inside a plain type after a binding: `:` (annotation), `=` (default), `,` (separator), `?` (optional), or `) =>`. A lone `(string | number)` fails because `|` isn't in the set. Rest/empty parens are *always* function types since they're invalid as parenthesized types — that asymmetry is load-bearing. Reusing the error-count-guarded `skip_parameter_start` keeps failed speculation invisible in the final diagnostics list.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_function_type.ts` (`(c, d) => string`, `([a]) => string`, `({a}) => string`) and `error/ts_function_type_err.ts` (`<>(a: A, b: B) => string`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "is_at_function_type skip_parameter_start lookahead", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt bounded lookahead + silent-probe + follower-set disambiguation for any `(`-ambiguous dual construct; adapt token sets; omit nothing portable. This capsule plus arrow-speculation-memo.md covers both of Biome's `(` disambiguation families.
