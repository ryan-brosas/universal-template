<!-- capsule-v2 -->
# AST-level node replacement & list splicing — how do you mutate an immutable CST from its typed wrapper?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** What is the public API shape for replace/transfer-trivia/splice on persistent trees, and what must it preserve?

## AstNodeExt / AstNodeListExt / AstSeparatedListExt
**Path/Symbol:** `crates/biome_rowan/src/ast/mutation.rs` (whole file, 229L; `AstNodeExt` :5-145).
**Signature:** `fn replace_node(self, prev_node: N, next_node: N) -> Option<Self>`; `fn splice<R: RangeBounds<usize>, I: IntoIterator<Item = Self::Node>>(self, range: R, replace_with: I) -> Self`.
**Data Shape:** All methods consume `self` and return a NEW root (`Option` when prev isn't a descendant) — the underlying green tree is never mutated in place. Separated-list splice works on (node, separator) pairs and multiplies indices by 2 (:208-217).

### Decisive source
```rust
// Lookup the first token of `prev_node` and `next_node`, and transfer the leading
// trivia of the former to the later
if let (Some(prev_first), Some(next_first)) = (prev_first, next_first) {
    let pieces: Vec<_> = prev_first.leading_trivia().pieces().collect();
    next_node = next_node.replace_token_discard_trivia(
        next_first.clone(),
        next_first.with_leading_trivia(pieces.iter().map(|piece| (piece.kind(), piece.text()))),
    )?;
}
// ... same for trailing trivia of last_token ...
self.replace_node_discard_trivia(prev_node, next_node)
```

**Flow:** `replace_node_discard_trivia` = single `replace_child` on the syntax node (path-copy to root) → the trivia-preserving variant FIRST rewrites next_node's boundary tokens to carry prev's leading/trailing trivia pieces, THEN swaps → list `splice` delegates to `splice_slots(range, iter)` with `Some(node)` per element; separated lists interleave `Some(node), Option<separator>`.
**Invariant:** Trivia lives ON TOKENS, so preserving formatting across replacement means explicitly copying boundary trivia pieces — otherwise every fix/comment-preserving transform silently reformats. Splice ranges are element-indexed for callers but slot-indexed internally (×2 for separators); mixing that up corrupts the alternating layout.
**Probe:** No dedicated rowan tests dir — consumers pin this behavior (e.g. `crates/biome_js_analyze` fixes build via these APIs and their spec snapshots assert preserved comments). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "AstNodeExt replace_node splice_slots", limit: 10, fields: ["signature", "name", "file"] });
```
Resolves `ast.mutation.AstNodeExt.replace_node` (:22-25).

## Verdict
Adopt the two-tier API (raw discard-trivia primitive + trivia-transferring convenience) for any persistent-tree edit surface; adapt naming; omit separated-list pairing if your grammar has no separator tokens.
