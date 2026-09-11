<!-- capsule-v2 -->
# Export named vs named-from rewind — how do you disambiguate `export {a}` from `export {a} from "m"` when only one lookahead token separates them?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** The `{...}` specifier lists differ between the two clause forms (exports need reference-identifier legality; from-clauses accept any literal export name) — how does the parser pick without duplicating list code, and how does it recover from `export { "a" as b }` (string local, illegal without `from`)?

## parse_export_named_or_named_from_clause
**Path/Symbol:** `crates/biome_js_parser/src/syntax/module.rs:parse_export_named_or_named_from_clause` (:739-748), `parse_export_named_clause` (:770-794), `parse_export_named_from_clause` (:1055-1085); recovery hook in `parse_any_export_named_specifier` (:857-888).
**Signature:** `fn parse_export_named_or_named_from_clause(p: &mut JsParser) -> ParsedSyntax` — checkpoint taken *before* attempting the plain clause.
**Data Shape:** Both clauses share the same opening tokens (`{` or `type {`). The rewind decision is a single token test (`p.at(T![from])`) after a full speculative parse of the first form.

### Decisive source
```rust
let checkpoint = p.checkpoint();
match parse_export_named_clause(p) {
    Present(_) if p.at(T![from]) => {
        p.rewind(checkpoint);
        parse_export_named_from_clause(p)
    }
    t => t,
}
// inside parse_any_export_named_specifier (plain form), the deliberate mis-parse:
parse_any_literal_export_name(p).or_add_diagnostic(p, expected_identifier);
// ... then a tailored error:
"A string literal cannot be used as an export binding without `from`."
```

**Flow:** checkpoint → parse `{ … }` as a *plain* named clause (specifiers parsed with reference-identifier rules; string/keyword locals are parsed-but-rejected with targeted errors) → if the next token is `from`, discard everything and re-parse with from-clause rules where those same locals are legal → otherwise keep the plain result plus its diagnostics.
**Invariant:** Speculation is allowed to produce diagnostics that will be discarded by the rewind — but the *mis-parse* of string locals exists precisely so the rewind branch triggers on well-formed from-clauses containing them; a porter who refuses to consume string locals here makes `export { "a" } from "./m"` unparseable. The semi is consumed inside each branch (both call `semi(...)`), so no terminator is double-eaten across the rewind boundary.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/export_named_clause.js` + `error/export_named_clause_err.js` (`export { default as "b" }`, string-local error text) and `ok/export_named_from_clause.js` (`export { "a" } from "./mod"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "parse_export_named_or_named_from_clause rewind", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt parse-cheap-form-then-rewind-on-trailing-token for prefix-shared clause pairs; adapt the trigger token set; omit the string-local accommodation if your specifier grammar has no such asymmetry. Coverage caveat: full-mode index, metadata_match.
