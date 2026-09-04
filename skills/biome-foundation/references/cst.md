<!-- capsule-v2 -->
# Rowan lossless CST core — how do you build a syntax tree that round-trips source losslessly without doubling node count?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** a lossless CST must keep whitespace/comments yet stay small and shareable; how does the green/red split, fixed-slot arity, hash-consing, and immutable mutation achieve that?

## The lossless-CST seam
**Path/Symbol:** `crates/biome_rowan/src/` — green layer (`green/{node,token,trivia,node_cache}.rs`), cursor layer (`cursor.rs`, `cursor/{node,token,trivia}.rs`), `tree_builder.rs`, `syntax_node_text.rs`, mutation region of `syntax/token.rs`.
**Signature:** `GreenNode`/`GreenToken`/`GreenTrivia` (immutable, thread-shared); red `SyntaxNode`/`SyntaxToken` (zipper cursors); `NodeCache` (hash-consing); `TreeBuilder`; `SyntaxNodeText`.
**Data Shape:** green tokens hold their FULL text (leading trivia + trimmed token + trailing trivia) in one inline UTF-8 allocation (`ThinArc<GreenTokenHead, u8>`, green/token.rs:139-146); `GreenTrivia` stores only `(TriviaPieceKind, length)` pairs — the chars are slices of the token's own buffer. Green nodes store a fixed-length array of `Slots` (`Node{rel_offset}` / `Token{rel_offset}` / `Empty{rel_offset}`), each exactly 2 words (static_assert :61).

### Decisive source
```rust
// green/trivia.rs:61-67 — trivia identity is (kind,length), not text (verbatim)
// "The identity of a trivia is defined by the kinds and lengths of its items but not by
//  the texts of an individual piece. That means, that \r and \n can both be represented by
//  the same trivia ... This is safe because the text is stored on the token to which the
//  trivia belongs."  (keeps GreenTrivia internable at exactly 8 bytes, asserted :186-189)
```
```rust
// green/node.rs:190-191 — fixed slot arity (verbatim)
// "Every node of a specific kind has the same number of slots to allow using fixed offsets
//  to retrieve a specific child even if some other child is missing."
```
**Flow:** parser → green tree (structure+text, relative offsets, NO parent pointers, built once, shareable across threads via vendored triomphe Arc) → red layer wraps each visited element in a heap `NodeData` (slot index, absolute `TextSize` offset, Rc parent) — a **zipper** over the purely functional green tree (cursor.rs:1-8: "Functional programmers will recognize that this module implements a zipper"). Red nodes fabricate lazily from (parent Rc, slot index, relative offset); siblings found by walking the PARENT's green slots from the current index (:170-215). Child red nodes hold raw NonNull *weak* pointers to green elements — sound because child→root→root-green→child-green forms a reference cycle keeping green alive (:33-40). The unsafety boundary is documented (cursor.rs:14: "The implementation is utterly and horribly unsafe... It is believed that the API here is, in principle, sound").
**Mutation:** NO in-place edit API. Every mutation clones the affected node's slot vector, splices replacements, rebuilds a new green node, returns a NEW detached root — `#[must_use]` (:218-219). If the target's Rc refcount is 1, the existing allocation is REUSED in place (:324-325) — copy-on-write via refcount uniqueness. `replace_child` walks the parent chain rebuilding one node per level (O(depth), :342-381). Purely functional updates keep old+new trees alive (batch edits/undo) while single-writer edits stay allocation-free.
**Hash-consing (NodeCache):** dedups tokens by (kind, text), nodes with ≤3 children by (kind, occupied-slot child pointers) using PRE-COMPUTED child hashes, trivia by piece sequence (permanently pinned single-whitespace instance). Comment (green/node_cache.rs:151-166): "if the tree is interned, then all of its children are interned as well... we just *know* hashes of children... use *raw* API of hashbrown and provide the hashes manually. Our manual Hash and the #[derive(Hash)] are actually different! ... we additionally wrap the data in Cached* wrappers." Cites Roslyn (:245-251): deduping saves 17% of green-node memory. Eviction uses a generation bit packed into the low bit of the green pointer (:27-77); `retain_cache()` (:346-360). Equality on collision compares kinds + occupied-slot pointers only — Empty-slot PATTERNS encode error-recovery shape, so two nodes differing only in which children are missing still compare unequal (tests :210-262). Sizes: CachedNode=16, CachedToken=8, CachedTrivia=8 (:365-369).
**Text reconstruction:** because every byte lives in a token, printing a node = concatenating token texts in pre-order (green/node.rs:152-161) — no separate source string, no positions to patch. `SyntaxNodeText` adds lazy chunk iteration, zero-copy slicing, allocation-free equality against `&str`, and a single-token fast path (:157-165).
**Invariant:** green tree is immutable + parent-free (shareable); every node kind has fixed slot arity with explicit `Empty` holes (positional access survives error recovery); trivia is (kind,length) over the token's own buffer (lossless without node bloat); interning keeps children interned so child hashes are known.
**Probe:** green/token.rs:209-218 builds token `"\n\t let \t\t"` asserting text/text_len(9)/text_trimmed("let"); cursor/trivia.rs:164-180 asserts leading/trailing trivia texts separately; :531-558 builds a SEPARATED_EXPRESSION_LIST with a missing comma asserting children().count()==2 but slots [0,2]; :560-566 asserts root.slots().len()==3; :300-330 asserts chunked-text equality across different chunk splits; tree_builder.rs:182-188 checkpoint-misuse panics ("checkpoint no longer valid, was finish_node called early?" / "was an unmatched start_node_at called?").

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "GreenNode GreenTrivia NodeCache hash-consing slot arity", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the green/red split (immutable parent-free green + transient zipper red), fixed-slot arity with Empty holes, (kind,length) trivia pinned to tokens, must_use immutable mutation with refcount reuse, and bottom-up hash-consing with cached child hashes; adapt slot kinds and language specifics; omit the vendored triomphe Arc and Roslyn-specific sizing unless matching them. Coverage caveat: the zipper has no direct test (identity semantics run everywhere); the rest is pinned by the in-file unit tests cited above.
