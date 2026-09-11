<!-- capsule-v2 -->
# YAML block-scope lexer — column borders, the sequence/map same-column asymmetry, and pseudo-token emission

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** How does a single-pass lexer decide block-structure closes for an indentation-delimited language, and where is YAML's nastiest scope rule encoded?

## Scope stack (biome_yaml_parser/src/lexer/mod.rs)
**Path/Symbol:** `crates/biome_yaml_parser/src/lexer/mod.rs:22` (`scopes: Vec<BlockScope>`), `:1808-1876` (`BlockScope::{Sequence(border), Map(border)}` + `contains`/`close_token_kind`), `:459-476` (`close_breached_scopes`).
**Data Shape:** `BlockScope::contains(coordinate: TextCoordinate { offset, column }, is_sequence_entry: bool)`; pseudo tokens carry only kind + coordinate.

### Decisive source
```rust
// lexer/mod.rs:1857-1868 — THE asymmetry (documented in-source)
fn contains(&self, coordinate: TextCoordinate, is_sequence_entry: bool) -> bool {
    match self {
        Self::Sequence(border) => {
            // Since a sequence entry can start on the same column as a map entry, we have to check
            // whether the current entry is a map or a sequence entry.
            // If it's a map entry and starts on the same column as the current sequence scope, it
            // belongs to the parent scope instead.
            coordinate.column > *border || (is_sequence_entry && coordinate.column == *border)
        }
        Self::Map(border) => coordinate.column >= *border,
    }
}
```

**Flow:** at every newline, `evaluate_block_scope` consumes trivia then pops scopes until one `contains` the new coordinate — each popped scope emits its close token as a PSEUDO token stamped at the breach coordinate (`LexToken::pseudo(scope.close_token_kind(), …)`), so MAPPING_END/SEQUENCE_END land BEFORE the next real token with zero-width spans. EOF → `close_all_scopes`.
**Invariant:** Map scopes are INCLUSIVE of their border column (`>=`); sequence scopes are exclusive UNLESS the incoming line is itself a `- ` entry on exactly the border column. A porter unifying both to `>` or `>=` breaks either sibling maps under sequences or same-column nesting — this predicate is the parser's whole notion of YAML block ownership. The sibling `indent()` method (:1830-1835) uses STRICT `>` for BOTH variants ("strictly belongs... doesn't share the scope's border") — indent-vs-contains is the two-predicate design; conflating them breaks same-column nesting. The lookahead helpers (`kind_after_properties` :49-75, `collection_content_has_preceding_line_break` :77-109) lex AHEAD into a token buffer without consuming, because `- [a,b]: x` vs `- [a,b]` can't be disambiguated until after properties+trivia skip.
**Probe:** `grep -n 'coordinate.column > \*border' crates/biome_yaml_parser/src/lexer/mod.rs` → 4 hits: `1833:`+`1834:` (indent, both variants strict `>`) and `1852:`+`1864:` (contains: sequence-exclusive + same-column-sequence carve-out); `grep -c 'LexToken::pseudo' crates/biome_yaml_parser/src/lexer/mod.rs` → `15` sites (scope closes at :472/:484 are the ones this capsule's flow cites; the rest synthesize START/END/EOF markers); `grep -n 'fn close_all_scopes' crates/biome_yaml_parser/src/lexer/mod.rs` → `481:`.

## Lexer shape context
`YamlLexer` (:14-33): source + TextCoordinate cursor + diagnostics + scope stack + `VecDeque<LexToken>` output buffer + `bom_allowed` (BOM legal only at doc prefix). `consume_tokens` loops "until the lexer found a disambiguated checkpoint" (:111-118 doc).
**Probe:** `grep -n 'bom_allowed' crates/biome_yaml_parser/src/lexer/mod.rs | head -1` → `31:`.

---
**Verdict:** ADOPT the contains() predicate + pseudo-token-at-breach design for any indentation-scoped lexer; the lookahead buffer pattern generalizes.
