<!-- capsule-v2 -->
# ASI contract — when is a semicolon "there" without being there, and what exactly does `semi` do when it isn't?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How must every statement terminator be written so ASI (EOF / `}` / line-break) is accepted, and where does the error point?

## semi / optional_semi / is_semi — one three-function terminator kernel
**Path/Symbol:** `crates/biome_js_parser/src/syntax/stmt.rs:semi` (:87-108), `optional_semi` (:115-121), `is_semi` (:123-128).
**Signature:** `pub(crate) fn semi(p: &mut JsParser, err_range: TextRange) -> bool`; `pub(crate) fn optional_semi(p: &mut JsParser) -> bool`; `pub(super) fn is_semi(p: &mut JsParser, offset: usize) -> bool`.
**Data Shape:** `semi` = strict variant: returns whether a (possibly implicit) terminator was consumed, emits the diagnostic on failure. `optional_semi` = silent variant: eats `;` if present else consults ASI, never errors. `is_semi(offset)` is the pure predicate used for lookahead.

### Decisive source
```rust
pub(super) fn is_semi(p: &mut JsParser, offset: usize) -> bool {
    p.nth_at(offset, T![;])
        || p.nth_at(offset, EOF)
        || p.nth_at(offset, T!['}'])
        || p.has_nth_preceding_line_break(offset)
}
// optional_semi: if p.eat(T![;]) { return true; }  is_semi(p, 0)
```

**Flow:** Every statement parser ends with `semi(p, TextRange::new(stmt_start, cur_end))`. On failure the diagnostic carries TWO details: `p.cur_range()` annotated "...Which is required to end this statement" points at `err_range` (the whole statement), while the current token is annotated as the offending position — porting only a single-span error loses the recovery hint quality. Callers that may legally omit the terminator call `optional_semi` instead (`do..while` after a well-formed parenthesized head :1578-1583, TS type-member separator fallback).
**Invariant:** The ASI predicate is EXACTLY `{explicit ;} ∨ {EOF} ∨ {'}' } ∨ {line break before next token}` — nothing else counts. A porter adding e.g. `)` or treating any line break anywhere as a terminator breaks `let foo = bar\nthrow foo` detection (`error/semicolons_err.js`).
**Probe:** `crates/biome_js_parser/tests/js_test_suite/ok/semicolons.js(.snap)` (newline-terminated statements parse clean) and `error/semicolons_err.js` (`let foo = bar throw foo` errors with the two-detail span).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "optional_semi is_semi has_nth_preceding_line_break statement terminator", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the single shared kernel + err_range convention for any hand-written parser with ASI-like rules (CSS semicolons, config grammars); adapt the token set to the host language's implicit-terminator rule; omit Biome's exact markup builders.
