<!-- capsule-v2 -->
# SyntaxFactory slot filling — how do fixed-slot grammars absorb missing/invalid children and still produce a well-formed green node?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does the factory decide between present, absent (empty slot), and bogus kinds from an arbitrary child stream?

## SyntaxFactory trait + RawNodeSlots
**Path/Symbol:** `crates/biome_rowan/src/syntax_factory.rs:SyntaxFactory` (:17-125), `RawNodeSlots<const COUNT: usize>` (:198-243), fix-up iterator `SeparatedListWithMissingNodesOrSeparatorSlotsIterator` (:129-186); concrete generated impls e.g. `crates/biome_js_factory/src/generated/factories.rs`.
**Signature:** `fn make_syntax(kind: Self::Kind, children: ParsedChildren<Self::Kind>) -> RawSyntaxNode<Self::Kind>`; helpers `make_node_list_syntax`, `make_separated_list_syntax`.
**Data Shape:** `ParsedChildren` = flat slice of already-built nodes/tokens; output = `RawSyntaxNode(kind, Vec<Option<RawSyntaxElement>>)` where `None` is a hole matching one grammar slot.

### Decisive source
```rust
// It's important that the factory function is idempotent... This is important because
// the returned nodes may be cached by `kind` and what `children` are present.
fn make_syntax(kind: Self::Kind, children: ParsedChildren<Self::Kind>) -> RawSyntaxNode<Self::Kind>;
```
Separated-list state machine (:79-107): alternate node/separator expectations; a separator where a node was expected ⇒ `missing_count += 1`; an element that can't cast ⇒ whole list becomes `kind.to_bogus()`; trailing separator without `allow_trailing` ⇒ one extra empty slot.

**Flow:** parser emits whatever it managed to parse → factory walks children once: for fixed-arity nodes, generated code marks each grammar slot Present/Absent (`RawNodeSlots`) then interleaves `None` holes at Absent positions; for lists, the generic validators either fill holes for missing separators/elements or demote the entire list kind to bogus.
**Invariant:** Slot ORDER is grammar truth — a `None` must appear exactly where the grammar's slot would sit, never compacted. The kind-demote-to-bogus path preserves all children (still lossless). Factories must not depend on call order or external state because results are hash-consed by (kind, children).
**Probe:** No dedicated rowan test dir — behavior pinned end-to-end by the js_test_suite snapshot corpus (e.g. `error/js/variable_declarator_list_empty.js` produces a bogus declarator list with correct slot layout); coverage caveat recorded honestly here.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SyntaxFactory make_syntax separated list missing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt slot-filling factories + bogus demotion for any fixed-slot CST; generate per-language factories rather than hand-writing them (Biome generates ~all of them); omit the const-generic COUNT machinery if your slots are unbounded lists only.
