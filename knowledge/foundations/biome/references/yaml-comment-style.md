<!-- capsule-v2 -->
# YAML comment placement & suppression — the Default-placement fallback and format-category gate

**Source:** biome MIT `main@6f7774dc` (drift plane pass 13); Codebase Memory `biome`. **Question:** How does a language with only line comments (`#`) define its CommentStyle, and which nodes can own dangling comments?

## YamlCommentStyle (biome_yaml_formatter/src/comments.rs)
**Path/Symbol:** `crates/biome_yaml_formatter/src/comments.rs:49-70` (`is_suppression`/`is_global_suppression`), `:315-330` (placement fn fallback arm).
**Signature:** implements `CommentStyle<Language = YamlLanguage>`; suppression detection reuses the shared `parse_suppression_comment` machinery.

### Decisive source
```rust
// comments.rs:54-60 — only CLASSIC biome-ignore comments suppress in YAML
fn is_suppression(text: &str) -> bool {
    parse_suppression_comment(text)
        .filter_map(Result::ok)
        .filter(|suppression| suppression.kind == SuppressionKind::Classic)
        .flat_map(|suppression| suppression.categories)
        .any(|(key, ..)| key == category!("format"))
}
```

**Flow:** placement function handles special node shapes first, but anything without a preceding node falls to `CommentPlacement::Default(comment)` (:325-327) — the kernel then attaches it leading/trailing per its own rules. Suppression check happens per-node inside FormatNodeRule BEFORE any formatting (see yaml-formatter-bootstrap), so suppressed subtrees reprint verbatim.
**Invariant:** Only `SuppressionKind::Classic` (i.e. `biome-ignore`) counts; other comment kinds never suppress — porters extending YAML tooling must keep lint-vs-format category separation (`category!("format")`). Comments.rs at 712L is the largest non-generated formatter file: most mass is per-node-kind placement rules for block maps/sequences/scalars where `#` comments can sit between every entry line.
**Probe:** `grep -c 'CommentPlacement::Default' crates/biome_yaml_formatter/src/comments.rs` → ≥1; `grep -n 'SuppressionKind::Classic' crates/biome_yaml_formatter/src/comments.rs | head -1` → `57:`; `wc -l crates/biome_yaml_formatter/src/comments.rs` → `712`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"YamlCommentStyle is_suppression placement","limit":5,"detail":"ids"}'
```
NOTE (retrieval-plane, audited 2026-08-24): `YamlCommentStyle.is_suppression` resolves rank-1 line-exact (:54-60). The sibling query "FormatYamlVerbatimNode format_suppressed_node bogus" hits TIED js/grit twins at -25.67 — use `limit: 8` so the YAML `format_suppressed_node` (`verbatim.rs` 233-239) surfaces; `search_code --pattern 'YamlCommentStyle'` is the fallback if BM25 drifts.

---
**Verdict:** ADOPT as the minimal CommentStyle template; extend placement per node kind only where YAML layout demands.
