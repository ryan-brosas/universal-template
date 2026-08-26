<!-- capsule-v2 -->
# Red-tree Root/Child memory model — why do child SyntaxNodes hold a raw pointer to their green node, and when is it sound?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How can cursor nodes be cheaply created/discarded during traversal (zipper over an immutable tree) without leaking or use-after-free, given green trees are shared Arc'd data?

## NodeData / NodeKind / WeakGreenElement
**Path/Symbol:** `crates/biome_rowan/src/cursor.rs:NodeData` (:74-83), `NodeKind` (:90-98), `WeakGreenElement` (:109-139), `next_sibling`/`prev_sibling` (:234-253), `splice_slots` (:313-334), `replace_child` (:342-379), `detach` (:296-308); child construction `crates/biome_rowan/src/cursor/node.rs:new_child` (:36-48), `Siblings::following/previous` (:900-947).
**Signature:** `enum NodeKind { Root { green: GreenElement }, Child { green: WeakGreenElement, parent: Rc<NodeData> } }` — a red node is *either* an owning root **or** a parent-referencing child; never both.
**Data Shape:** `NodeData { kind, slot: u32, offset: TextSize }`; identity key is `(NonNull<GreenData>, offset)` (`NodeData::key`, :156-166). Absolute text range = `TextRange::at(offset, green.text_len())`.

### Decisive source
```rust
// The soundness argument lives in the module docs:
// NodeData refcount == outstanding SyntaxNode/SyntaxToken handles
//   + children with non-zero refcounts.
// A lone handle mid-tree keeps exactly its ancestor path alive (each Rc=1).
//
// Child -> green is a RAW pointer. Sound because the only path to dropping a
// green subtree is dropping the ROOT NodeData, and every live child holds a
// strong Rc chain to that root (cycle: child NodeData -> root NodeData ->
// root GreenNode -> child GreenNode keeps greens alive as long as any red handle exists).
let siblings = self.green_siblings()?;               // parent's green slots
siblings.following().find_map(|child| {
    let parent = self.parent_node()?;
    let offset = parent.offset() + child.rel_offset();  // absolute offsets recomputed per hop
    Some(SyntaxNode::new_child(green, parent, child.slot(), offset))
})
```

**Flow:** traversal materializes transient `Rc<NodeData>` per visited node → siblings iterate the *parent's green slot array* directly (no red allocation for skipped elements) → mutations (`splice_slots`, `replace_child`) rebuild green paths bottom-up and return a fresh owning root — reusing the existing allocation in place iff `Rc::get_mut` says the old red node is uniquely held.
**Invariant:** Never store a child's weak green pointer beyond the life of its parent chain — the type system doesn't stop you, the ownership protocol does (this is the documented unsafety boundary of the whole module). Offsets are *per-node cached* but must be threaded from the parent on every construction; computing them lazily would cost O(depth) per access, caching them globally would break under mutation since green nodes are position-free.
**Probe:** in-module `crates/biome_rowan/src/cursor/node.rs` `#[cfg(test)] mod tests::slots_iter` pins bidirectional slot iteration semantics (size_hint + next_back) that sibling navigation builds on.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "NodeData NodeKind WeakGreenElement new_child Siblings", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the root-or-child dichotomy + raw green pointers guarded by an Rc-to-root invariant for zipper-style cursors over persistent trees; adapt Rc→arena/GC per host language; omit allocation reuse if your host has no unique-ownership check. Coverage caveat: full-mode index, metadata_match.
