<!-- capsule-v2 -->
# Conditional-consequent arrow guard — when does an arrow body `({`/`([` inside a ternary consequent get misread as a return-type annotation, and what unbounded scan fixes it?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the parser prevent the ternary `:` in `cond ? x => ({a,b}) => body : alt` from being consumed as a TS return type by the speculative arrow parser?

## is_paren_group_followed_by_fat_arrow depth scan
**Path/Symbol:** `crates/biome_js_parser/src/syntax/function.rs:parse_arrow_body` (:934-979, guard at :954-976) and `is_paren_group_followed_by_fat_arrow` (:905-932).
**Signature:** `fn is_paren_group_followed_by_fat_arrow(p: &mut JsParser) -> bool` — requires `p.at(T!['('])`, pure multi-token lookahead (`p.nth(offset)`), consumes nothing.
**Data Shape:** Walks forward counting open `(` depth; at the first `)` that closes the *outermost* paren (depth returns to 0) returns whether the immediately following token is `=>`; EOF ⇒ false. No nesting of other bracket kinds is tracked — parens only.

### Decisive source
```rust
// Special case: when the body starts with `({` or `([`, it is ambiguous:
//   cond ? x => ({ a, b }) => body : alt  // `({a,b})` is a destructured parameter
//   cond ? x => ({ key: val }) : alt      // `({key:val})` is an object expression
// In TypeScript mode, the speculative arrow parser can misread the ternary `:`
// as a return-type annotation and treat the alternate's `=>` as the arrow. To
// avoid this, we block speculative arrow parsing unless `=>` immediately follows
// the `)`. If `=>` is there, the `({` or `([` is a destructured parameter and we allow it.
let body_context = context.and_in_conditional_consequent(false);
if context.is_in_conditional_consequent()
    && matches!(p.cur(), T!['('])
    && matches!(p.nth(1), T!['{'] | T!['['])
    && !is_paren_group_followed_by_fat_arrow(p)
{
    parse_assignment_expression_or_higher_no_arrow(p, body_context)
} else {
    parse_assignment_expression_or_higher(p, body_context)
}
```

**Flow:** arrow body is expression-form → clear `in_conditional_consequent` for the nested body (past the consequent top, guard no longer needed) → if entering from a conditional consequent AND body starts `({`/`([` AND the paren group's closing `)` is not immediately followed by `=>`, parse with `no_arrow` so the speculative path can't grab the alternate's `=>`.
**Invariant:** The depth counter must track *nested* parens (`(a: () => T) =>` would stop at the inner `)` without it). The guard fires **only** in conditional-consequent context and only for `(` + `{`/`[` bodies; everywhere else object/array arrow bodies stay on the normal path. Clearing `in_conditional_consequent` before recursing is what keeps the guard from leaking into nested non-ternary code.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/conditional_arrow_object_body_in_consequent.ts` (`? i => ({ [CONTENT_SLOT]: i }) : i => …`) and `conditional_arrow_return_type_in_consequent.ts` / `conditional_async_destructured_arrow_return_type.ts` (the `=>`-follows-paren cases that must still parse as arrows).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "is_paren_group_followed_by_fat_arrow conditional consequent arrow body", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the pattern (context flag + cheap bounded-scan disambiguator before committing to a speculative parse); adapt token names to host lexer; omit Biome-specific diagnostics. This is the repo's canonical answer to "speculative parser ate my delimiter".
