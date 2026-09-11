<!-- capsule-v2 -->
# Range-restricted traversal — how does `--range` filtering skip whole subtrees without missing boundary nodes?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** when a user requests analysis of one range, the visitor must skip everything outside it cheaply — what ordering comparison makes subtree-skip correct for nodes that merely overlap the range?

## The range-gate seam
**Path/Symbol:** `crates/biome_analyze/src/syntax.rs` — `SyntaxVisitor::visit` (:64-91), `Ast<N>` Queryable (:12-36); duplicated verbatim in `analyzer_plugin.rs` PluginVisitor (:148-153) and BatchPluginVisitor (:290-295).
**Signature:** `if let Some(range) = ctx.range && node.text_range_with_trivia().ordering(range).is_ne() { self.skip_subtree = Some(node.clone()); return; }`.
**Data Shape:** `skip_subtree: Option<SyntaxNode<L>>` latches the OUTSIDE node; comparison uses `TextRange::ordering` (a total order: Less = entirely before, Greater = entirely after, Equal/Intersecting = relevant) — NOT a contains() test.

### Decisive source
```rust
// syntax.rs:78-90 — Enter-only gate; Leave clears the latch by NODE IDENTITY;
// matching nodes use text_range_WITH_trivia so a node whose trivia touches the
// range still counts:
if self.skip_subtree.is_some() { return; }
if let Some(range) = ctx.range
    && node.text_range_with_trivia().ordering(range).is_ne()
{
    self.skip_subtree = Some(node.clone());
    return;
}
ctx.match_query(node.clone());
```
**Flow:** on every Enter: already-inside-a-skipped-subtree ⇒ return; node ordered NE (strictly before or after) the filter ⇒ latch this node and return (its entire subtree is outside); otherwise emit as a query match. On Leave: if the leaving node IS the latch, clear it. Because the walk is depth-first, one latch per level suffices. The same triple (latch, ordering-NE gate, identity-clear) is copy-pasted into both plugin visitors, and plugin visitors additionally cache `applies_to_file` lazily on first qualifying Enter (`FileApplicability::Unknown→Applicable|NotApplicable`) since the path is constant for the walk (:161-171, BatchPluginVisitor caches a Vec<bool> via get_or_insert_with :303-308).
**Invariant:** the gate must run BEFORE match_query but AFTER the skip-latch check, and clearing is by structural node equality — porters who use `contains(range)` instead of full ordering drop nodes that PARTIALLY overlap the filter edges; porters who clear the latch on ANY Leave unskip too early in sibling subtrees.
**Probe:** `crates/biome_analyze/src/syntax.rs` test `syntax_visitor` (:126-217) pins the no-range path (exact kind sequence); the range path is pinned upstream by biome's CLI range-format/lint fixture suites; lib.rs tests :992-1019 pin the related AnalysisFilter::match_plugins gating (disabled-group wins over enabled, lint-category-only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SyntaxVisitor skip_subtree text_range ordering", limit: 10, fields: ["signature", "name", "file"] });
// SyntaxVisitor.visit syntax.rs 64-91 (line-exact)
```

## Verdict
Adopt the latch + TextRange::ordering(NE) subtree skip with identity-based release and the lazy per-file applicability cache for expensive predicates; adapt the filter type; omit plugin batching unless you have >1 dynamic plugin. Coverage caveat: direct test covers only the unfiltered path — the NE-vs-contains distinction rests on source reading.
