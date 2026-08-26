<!-- capsule-v2 -->
# YAML verbatim/bogus/suppressed printer — one struct, three kinds, and the comment-rescue choreography

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** When a formatter must reprint a subtree byte-for-byte (syntax errors, suppression comments), how does it avoid dropping comments that physically live in surrounding trivia — and why not just call `node.text()`?

## The single implementation (biome_yaml_formatter/src/verbatim.rs)
**Path/Symbol:** `crates/biome_yaml_formatter/src/verbatim.rs:27-38` (`format_yaml_verbatim_node`, `#[expect(dead_code)]` + format_comments:false), `:224-230` (`format_bogus_node`, comments:true), `:233-239` (`format_suppressed_node`, comments:true).
**Signature:** all three construct `FormatYamlVerbatimNode { node, kind: VerbatimKind::{Verbatim{length}|Bogus|Suppressed}, format_comments }`.

### Decisive source
```rust
// verbatim.rs:17-22 — WHY the text() detour exists (source maps!)
/// You may be inclined to call `node.text` directly. However, using `text` doesn't track the nodes
/// nor its children source mapping information, resulting in incorrect source maps for this subtree.
```
```rust
// :58-70 — root nodes preserve OUTER trivia; children print trimmed ranges
let preserve_outer_trivia = self.node.parent().is_none();
let verbatim_source_range = if preserve_outer_trivia {
    source_range(f, self.node.text_range_with_trivia())
} else { ... trimmed_source_range(self.node) ... };
```

**Flow:** open `Tag::StartVerbatim(kind)` → walk descendants: every token `track_token`-ed; descendant comments partitioned by position into before/after the verbatim range and `mark_formatted()`-ed so they won't double-print (:79-104) → leading comments OUTSIDE the trimmed range printed if `format_comments`; those INSIDE are silently marked (:112-136) → original source slice via source_map when present else node text, `normalize_newlines(..., LINE_TERMINATORS)` → dangling comments marked → trailing outside-range comments → `Tag::EndVerbatim`.
**Invariant:** Comments physically sitting in the node's own trivia but attached to DESCENDANTS must be printed here or they vanish — this is the drop-prevention core. Skipped-token trivia extends the verbatim start (`take_while(start < verbatim_source_range.start())` :146-157) because "comments only format **up to** but not including skipped token trivia". The dead_code on format_yaml_verbatim_node is deliberate scaffolding: Verbatim-kind printing isn't wired yet; Bogus/Suppressed are.
**Probe:** `grep -c 'mark_formatted' crates/biome_yaml_formatter/src/verbatim.rs` → `4` call sites (descendant sweep, leading in-range, dangling, trailing); `grep -n 'preserve_outer_trivia' crates/biome_yaml_formatter/src/verbatim.rs | head -1` → `58:`; `grep -c '#\[expect(dead_code)\]' crates/biome_yaml_formatter/src/verbatim.rs` → `1`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"FormatYamlVerbatimNode format_suppressed_node bogus","limit":5,"detail":"ids"}'
```

---
**Verdict:** ADOPT for any language needing lossy-parse resilience; the descendant-comment rescue is mandatory in every port.
