<!-- capsule-v2 -->
# FormatLanguage entry pipeline — how do you run a language formatter end-to-end without losing track of a pre-processed tree?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** every prettier-family formatter needs an entry point that optionally rewrites the CST before printing — where does the transformed tree go, and what debug assertions must fire before a result is trusted?

## The transform-reinsertion + assertion pipeline
**Path/Symbol:** `crates/biome_formatter/src/lib.rs` — `FormatLanguage` trait (:1662-1720), `format_node` (:1709-1719), `format_node_with_source_map_generation` (:1723-1794), `format_node_with_offset` (:1799-1873).
**Signature:** `pub fn format_node<L: FormatLanguage>(root: &SyntaxNode<L::SyntaxLanguage>, language: L, delegate_fmt_embedded_nodes: bool) -> FormatResult<Formatted<L::Context>>`.
**Data Shape:** input = root node + language strategy object implementing `FormatLanguage { SyntaxLanguage, Context: CstFormatContext, FormatRule }`. Output = `Formatted<Context>` holding the IR `Document` + the context (comments map + optional `TransformSourceMap`). Failure = `FormatError` propagated from any rule via `?`.

### Decisive source
```rust
// lib.rs:1743-1775 — the transform's node is spliced BACK into its parent tree:
let (root, source_map) = match language.transform(root) {
    Some((transformed, source_map)) => {
        if &transformed == root { (transformed, Some(source_map)) }
        else {
            match root.ancestors().skip(1).last() {   // ancestors() yields self first!
                None => (transformed, Some(source_map)),
                Some(top_root) => {
                    let transformed_root = top_root
                        .replace_child(root.clone().into(), transformed.into())
                        // SAFETY: `root` is part of the `top_root` subtree.
                        .unwrap();
                    let transformed = transformed_root.covering_element(TextRange::new(
                        root_range.start(), root_range.start() + transformed_range.len()));
                    let node = match transformed {
                        NodeOrToken::Node(node) => node,
                        NodeOrToken::Token(token) =>
                            token.parent().unwrap_or(transformed_root),  // x2 in file
                    };
                    (node, Some(source_map))
                }
            }
        }
    }
    None => (root.clone(), None),
};
```
```rust
// lib.rs:1780-1793 — the four mandatory post-write checks:
let mut document = Document::from(buffer.into_vec());
document.propagate_expand();
state.assert_formatted_all_tokens(&root);   // debug: every token printed exactly once
state.assert_no_audit_events();             // debug: no unresolved speculative decisions
let context = state.into_context();
comments.assert_checked_all_suppressions(&root);  // :1790
comments.assert_formatted_all_comments();         // :1791
```
**Flow:** (1) call `language.transform(root)`; if it returns a rewritten tree AND the root has a parent, splice the transformed subtree back under `top_root` and re-resolve via `covering_element` (token results climb to `.parent()`). (2) Build context (`create_context(root, source_map, delegate_fmt_embedded_nodes)`), wrap root in `FormatRefWithRule::new(&root, L::FormatRule::default())` (:1774, second site :1850 for the offset variant). (3) `FormatState` → `VecBuffer` → `write!` → `Document::from` → `propagate_expand()`. (4) Run the four debug assertions. (5) `state.into_context()` hands comments back inside the returned `Formatted`.
**Invariant:** a transformed node is NEVER formatted in isolation when it lives inside a larger tree — the splice-back step keeps ancestor links valid so verbatim printing and comment lookups can walk upward; a porter who formats the detached transformed root loses suppression checking against the original tree. The `skip(1)` on `ancestors()` exists because rowan's iterator yields `self` first. `SourceMapGeneration::Disabled` is the default through `format_node` (:1717); only `format_sub_tree`/tests opt into Enabled at this layer.
**Probe:** `grep -n 'pub fn format_node_with_source_map_generation' crates/biome_formatter/src/lib.rs` → 1 hit :1723; `grep -c 'token.parent().unwrap_or(transformed_root)' crates/biome_formatter/src/lib.rs` → 2 (both entry variants); `grep -n 'comments.assert_checked_all_suppressions(&root)' …` → :1790+:1867; `grep -n 'state.assert_formatted_all_tokens(&root)' …` → :1784+:1861; direct tests: `disabled_source_map_generation_omits_source_position_elements` (:2991) vs `enabled_source_map_generation_inlines_source_position_on_text` (:3008) pin MappedText emission per generation flag.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"format_node_with_source_map_generation"}'
# biome.crates.biome_formatter.src.lib format_node_with_source_map_generation Function 1723-1794
```

## Verdict
Adopt the entry pipeline shape (transform → splice-back → single FormatState → four assertions); adapt `is_range_formatting_node`/`create_context` to your language's root-selection policy; omit the offset variant unless your host supports shifted-tree roots. Coverage: check_index_coverage `partial` ONLY at :2438-2443 (inside tests module); production ranges fully indexed, metadata_match, generation 2026-08-16T00:20:04Z.
