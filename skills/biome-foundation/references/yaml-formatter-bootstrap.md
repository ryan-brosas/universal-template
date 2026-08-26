<!-- capsule-v2 -->
# YamlFormatLanguage bootstrap — how a new language plugs into biome_formatter with only four impls

**Source:** biome MIT `main@6f7774dc` (new YAML stack, drift plane pass 13); Codebase Memory `biome`. **Question:** A porter adding a language formatter must reproduce exactly which traits/impls the kernel requires — YAML is the minimal worked example (compare js-formatter-language-integration).

## The required surface (biome_yaml_formatter/src/lib.rs)
**Path/Symbol:** `crates/biome_yaml_formatter/src/lib.rs:187-242` (`FormatNodeRule`), `:254-287` (`YamlFormatLanguage` + `FormatLanguage`), `:291-331` (token rule + AsFormat/IntoFormat for tokens), `:37-148` (AsFormat/IntoFormat/FormattedIterExt blanket adapters).
**Signature:** `FormatLanguage for YamlFormatLanguage { SyntaxLanguage=YamlLanguage, Context=YamlFormatContext, FormatRule=FormatYamlSyntaxNode }`.

### Decisive source
```rust
// lib.rs:270-272 — range formatting is UNCONDITIONALLY allowed (JS gates this per node!)
fn is_range_formatting_node(&self, _node: &SyntaxNode<Self::SyntaxLanguage>) -> bool {
    true
}
```
```rust
// lib.rs:191-199 — the node-rule template: suppression check FIRST, then comment sandwich
fn fmt(&self, node: &N, f: &mut YamlFormatter) -> FormatResult<()> {
    if self.is_suppressed(node, f) || self.is_global_suppressed(node, f) {
        return biome_formatter::write!(f, [format_suppressed_node(node.syntax())]);
    }
    self.fmt_leading_comments(node, f)?;
    self.fmt_fields(node, f)?;          // the ONLY method a per-node rule writes
    self.fmt_dangling_comments(node, f)?;
    self.fmt_trailing_comments(node, f)
}
```

**Flow:** entry fns `format_range/format_node/format_sub_tree` (:344-374) are thin forwarders to `biome_formatter::{format_range, format_node, format_sub_tree}` → context built in `create_context`: `Comments::from_node(root, &YamlCommentStyle, source_map)` then `.with_source_map`. Token printing tracks every token via `f.state_mut().track_token(token)` BEFORE trivia (:298) — same contract the JS formatter's pass-12 capsule documents; skipping it breaks range/source-map accounting.
**Invariant:** `create_context` IGNORES `_delegate_fmt_embedded_nodes` (YAML is never an embedded host yet). The default dangling-comments handler wraps in soft_block_indent and the doc comment warns it "isn't ideal but ensures that no comments are dropped" — node rules that CAN dangle comments should override. Suppression = verbatim reprint via `format_suppressed_node`, checked per-node AND globally.
**Probe:** `grep -c 'pub fn format_' crates/biome_yaml_formatter/src/lib.rs` → `3`; `grep -n 'track_token' crates/biome_yaml_formatter/src/lib.rs` → `298:`; `grep -c 'impl.*AsFormat<YamlFormatContext>' crates/biome_yaml_formatter/src/lib.rs` → `1`; smoke test pins round-trip: `grep -n 'foo: bar' crates/biome_yaml_formatter/src/lib.rs` → `384:`+`389:`.

## Get live surrounding code
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","query":"YamlFormatLanguage FormatNodeRule create_context","limit":5,"detail":"ids"}'
```

---
**Verdict:** ADOPT as the checklist skeleton for new-language formatters: 3 entry forwards + FormatLanguage + FormatNodeRule template + token rule + comment style + options struct.
