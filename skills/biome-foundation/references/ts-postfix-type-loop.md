<!-- capsule-v2 -->
# Postfix type loop — why must `[` postfix types refuse line breaks, and how do `string[]`, `string[number]`, and `string[number][]` share one loop?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser choose `TS_ARRAY_TYPE` vs `TS_INDEXED_ACCESS_TYPE` inside a single postfix loop, and what breaks without the line-break guard?

## parse_postfix_type_or_higher
**Path/Symbol:** `crates/biome_js_parser/src/syntax/typescript/types.rs:parse_postfix_type_or_higher` (:849-874).
**Signature:** `fn parse_postfix_type_or_higher(p: &mut JsParser, context: TypeContext) -> ParsedSyntax` — called from `parse_ts_primary_type` with `.and_allow_conditional_types(true)` (postfix position re-enables conditionals).
**Data Shape:** Loop over `p.at(T!['[']) && !p.has_preceding_line_break()`; per iteration completes either `TS_INDEXED_ACCESS_TYPE` (inner type present) or `TS_ARRAY_TYPE` (absent).

### Decisive source
```rust
while p.at(T!['[']) && !p.has_preceding_line_break() {
    let m = left.precede(p);
    p.bump(T!['[']);
    left = if parse_ts_type(p, context).is_present() {
        // type A = string[number];
        // type B = string[number][number][number][];
        p.expect(T![']']);
        m.complete(p, TS_INDEXED_ACCESS_TYPE)
    } else {
        // type A = string[];
        p.expect(T![']']);
        m.complete(p, TS_ARRAY_TYPE)
    }
}
```

**Flow:** primary → loop { precede, bump `[`, try full inner type; present ⇒ indexed access, absent ⇒ array; expect `]` } — chained mixes like `string[number][][]` fall out naturally because each iteration re-precedes the previous completed node.
**Invariant:** The line-break guard is ASI-critical: in member positions `foo(): string\n[]` would otherwise glue an array suffix onto the return type across the newline. Absent-vs-present of ONE inner parse is the entire array/indexed decision — no token lookahead past `[`. The conditional-types re-enable matters for `A extends B ? C : D[]`-style nesting reached through postfix.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/ts_indexed_access_type.ts` / `ok/ts_array_type.ts` equivalents cited inline (:858-867); combined chain `type B = string[number][number][number][];`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_postfix_type_or_higher indexed access array type", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-loop postfix folding with presence-based kind choice and the line-break guard; adapt kinds; omit nothing portable.
