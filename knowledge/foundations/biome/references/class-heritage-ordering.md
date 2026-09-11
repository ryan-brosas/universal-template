<!-- capsule-v2 -->
# Class heritage clause ordering — how do you accept extends/implements in any order but enforce the legal sequence with precise diagnostics?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** `class B implements I extends A` is illegal TS, `class A extends B extends C {}` and comma-separated extends are illegal everywhere — what loop structure parses all of them while keeping first-occurrence ranges for the error details?

## eat_class_heritage_clause
**Path/Symbol:** `crates/biome_js_parser/src/syntax/class.rs:eat_class_heritage_clause` (:331-397), `parse_extends_clause` (:404-447), `parse_extends_expression` (:449-461).
**Signature:** `fn eat_class_heritage_clause(p: &mut JsParser)` — eats clauses into whatever node is currently open (called between type parameters and `{`).
**Data Shape:** Two `Option<CompletedMarker>` slots (`first_extends`, `first_implements`) retained across iterations purely to source *ranges* for diagnostics; the loop runs until the current token is neither keyword.

### Decisive source
```rust
loop {
    match p.cur() {
        T![extends] => {
            let current = parse_extends_clause(p).expect("...");
            match first_extends.as_ref() {
                None => {
                    first_extends = Some(current);
                    if let Some(first_implements) = first_implements.as_ref() {
                        p.error(err_builder("'extends' clause must precede 'implements' clause.", current.range(p))
                            .with_detail(first_implements.range(p), "This is where implements was found"));
                    }
                }
                Some(first) => p.error("'extends' clause already seen." /* + first range detail */),
            }
        }
        T![implements] => { /* symmetric; ALSO: in JS files the FIRST implements is
                             change_to_bogus'd with a ts-only error (:373-380) */ }
        _ => break,
    }
}

// inside parse_extends_clause — trailing-comma recovery keeps parsing extra parents:
while p.at(T![,]) {
    let comma_range = p.cur_range();
    p.bump(T![,]);
    let extra = p.start();
    if parse_extends_expression(p).is_absent() {
        p.error("Trailing comma not allowed."); extra.abandon(p); break;
    }
    parse_ts_type_arguments(p, TypeContext::default()).ok();
    p.error("Classes can only extend a single class." /* over extra_class range */);
}
// parse_extends_expression refuses `extends {} {`-style body confusion:
if p.at(T!['{']) && p.nth_at(1, T!['}']) &&
   !matches!(p.nth(2), T![extends] | T![implements] | T!['{'] | T![,]) { return Absent; }
```

**Flow:** repeatedly consume whichever clause appears → first occurrence of each records its marker → second occurrences and order violations emit immediately with both ranges → each extends clause itself tolerates `, more-expressions` so the class body still parses after malformed heritage.
**Invariant:** Diagnostics never rewind: an out-of-order or duplicate clause stays in the tree at its written position (bogus-ed only when language-illegal), because snapshot tests pin exact error spans. The `{}` lookahead guard prevents `class A extends {}` from eating the class's own body braces as an object literal — a porter omitting it mis-parses every nameless-base class.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/ts_class_heritage_clause_errors.ts` (pins `implements Int extends A`, double implements, empty extends/comma cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "eat_class_heritage_clause parse_extends_clause", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt first-occurrence slot tracking for ordered-clause validation in any declaration grammar; adapt clause keywords; omit the bogus-on-JS demotion if your host has no dialect gate. Coverage caveat: full-mode index, metadata_match.
