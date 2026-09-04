<!-- capsule-v2 -->
# Separated-list trailing-comma state machine — how does one iterator encode Allowed/Disallowed/Mandatory/Omit trailing separators?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** every prettier-family formatter needs per-language trailing-comma policy over AST lists that may or may not carry a source separator — what is the single kernel and its four-way contract?

## The separated seam
**Path/Symbol:** `crates/biome_formatter/src/separated.rs` — `FormatSeparatedElement::fmt` (:52-120), `FormatSeparatedIter` look-ahead iterator (:124-221), `TrailingSeparator` enum (:224-238), `FormatSeparatedOptions { trailing_separator, group_id, nodes_grouped }` (:241-245).
**Signature:** `FormatSeparated::new(node.elements(), ",", FormatSeparatedElementRule).nodes_grouped().with_trailing_separator(TrailingSeparator::Allowed)` (builder chain); `is_last` computed by ONE-element look-ahead (`self.next = self.inner.next()`).
**Data Shape:** `AstSeparatedElement { node: SyntaxResult<N>, separator: Option<SyntaxToken> }` — rowan stores separators as optional trailing tokens, so the SAME code path must handle present and absent separators for the last element.

### Decisive source
```rust
// separated.rs:73-111 — four policies × two worlds (separator present / absent):
if let Some(separator) = separator {
    if self.is_last {
        match self.options.trailing_separator {
            TrailingSeparator::Allowed => {
                // format_replaced removes ONLY the token when the group doesn't
                // break but still prints its trivia unconditionally:
                format_only_if_breaks(separator, &format_separator, self.on_skipped)...
            }
            TrailingSeparator::Mandatory   => write!(f, [format_separator])?,
            TrailingSeparator::Disallowed  => return Err(FormatError::SyntaxError),
            TrailingSeparator::Omit        => (self.on_removed)(separator, f)?,
        }
    } else { write!(f, [format_separator])?; }
} else if self.is_last {
    match self.options.trailing_separator {
        TrailingSeparator::Allowed =>
            write!(f, [if_group_breaks(&token(self.separator)).with_group_id(...)])?,
        TrailingSeparator::Mandatory => token(self.separator).fmt(f)?,
        _ => { /* no op */ }
    }
} else {
    unreachable!("This is a syntax error, separator must be present between every two elements");
}
```
**Flow:** non-last elements always print their separator verbatim. Last element: present-separator world — Allowed wraps it in `format_only_if_breaks` (drop on fit, keep trivia), Mandatory prints it, Disallowed is a SYNTAX ERROR that opts out of formatting entirely, Omit calls `on_removed`; absent-separator world — Allowed synthesizes `if_group_breaks(",")`, Mandatory synthesizes unconditionally, Omit/Disallowed no-op. `nodes_grouped` optionally wraps each element in its own group so multi-line elements break independently of the list group.
**Invariant:** the mid-list `unreachable!` encodes a parser guarantee — a missing separator BETWEEN elements can never reach formatting. The Allowed-with-present-separator path MUST use `format_replaced`-style removal (not plain token skip) or the separator's attached comments vanish when the comma is dropped — the in-source comment at :79-81 states exactly this.
**Probe:** direct consumers pin all four arms end-to-end through real formatter specs — `crates/biome_js_formatter/tests/specs/js/module/array/trailing-commas/{es5,none}/array_trailing_commas.js(+snap)` (Allowed vs Omit policy outcomes), object twin under `.../object/trailing-commas/`; `crates/biome_css_formatter/src/separated.rs` re-uses the trait surface for SCSS lists.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "FormatSeparatedIter TrailingSeparator format_separated", limit: 10, fields: ["signature", "name", "file"] });
// FormatSeparatedElement.fmt separated.rs 59-120 (line-exact)
```

## Verdict
Adopt the four-policy kernel verbatim for any list with configurable trailing commas; adapt the rule trait to your node type; omit Disallowed only for grammars where it truly cannot occur (then debug_assert instead of erroring). Coverage caveat: kernel itself has no in-crate unit tests; behavior is pinned by language-formatter snapshot suites.
