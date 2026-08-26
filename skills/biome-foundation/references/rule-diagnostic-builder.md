<!-- capsule-v2 -->
# RuleDiagnostic builder — what belongs to the diagnostic vs. the analyzer, and how do embedded offsets reach advice frames?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** rules build diagnostics before knowing severity, file, or embedding offset — which builder methods are safe for rule authors and which fields does the ENGINE own?

## The RuleDiagnostic seam
**Path/Symbol:** `crates/biome_analyze/src/rule.rs` — `RuleDiagnostic::new` (:1656-1668), advice model `RuleAdvice { details, notes, suggestion_list, parent_advices }` (:1630-1638), `Advices::record` order (:1588-1627), `set_advice_offset` (:1670-1675), tag builders (`deprecated/unnecessary/verbose`) (:1681-1701), `label/detail/note/warning/footer_list/with_advices/subcategory/with_severity` (:1703-1781), `RuleAction` (:1785-1810), `SuppressAction` (:1813-1817).
**Signature:** `pub fn new(category: &'static Category, span: impl AsSpan, title: impl Display) -> Self`; builders consume self and return Self.
**Data Shape:** details are `(LogCategory, MarkupBuf, Option<TextRange>)` printed as log + frame pairs; notes are `(LogCategory, MarkupBuf)` footers; `suggestion_list` renders via `visitor.record_list`; `parent_advices: Vec<SerializableAdvices>` carry foreign Advices that can be re-offset (`offset_by`); `advice_offset: Option<TextSize>` is engine-set.

### Decisive source
```rust
// rule.rs:1589-1602 — print order is DETAILS (each with its own frame, shifted
// when BOTH range and advice_offset exist), then NOTES, then suggestion list,
// then parent advices:
for detail in &self.rule_advice.details {
    visitor.record_log(detail.log_category, &markup! { {detail.message} }.to_owned())?;
    if let (Some(span), Some(advice_offset)) = (detail.range, self.advice_offset) {
        let span = span.add(advice_offset);
        let location = Location::builder().span(&span).build();
        visitor.record_frame(location)?;
    } else {
        let location = Location::builder().span(&detail.range).build();
        visitor.record_frame(location)?;
    };
}
```
**Flow:** `new` starts severity at default and tags empty — the ENGINE overwrites severity from metadata at signal time (signals.rs:536) so `with_severity` exists ONLY for plugins (doc comment :1773-1777). `verbose()` marks diagnostics shown solely under --verbose; `deprecated()/unnecessary()` map to LSP tags; `subcategory` feeds plugin signal naming. `footer_list` is the only way to render a bulleted suggestion block. `RuleAction::new(category, applicability, message, mutation)` is the fix payload the analyzer wraps into AnalyzerAction (applicability read back through `action.applicability()` when config doesn't override).
**Invariant:** markup is data end-to-end (MarkupBuf, never pre-rendered strings); advice print ORDER (details→notes→list→parents) is user-visible contract; rule authors must not set severity; every Detail's frame shifts only when a range exists — rangeless notes never shift under embedded offsets.
**Probe:** upstream snapshot tests of rendered diagnostics (e.g. biome_diagnostics display snapshots + rule expect_diagnostic fences) pin the print order and footer shapes; no direct unit test on RuleAdvice — the record() body above is the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "RuleDiagnostic label note footer_list set_advice_offset", limit: 10, fields: ["signature", "name", "file"] });
// RuleAdvice rule.rs 1630-1638; Advices::record 1588-1627 (line-exact)
```

## Verdict
Adopt the four-slot advice model with fixed print order, engine-owned severity, tag-based LSP hints, and offset-shifted detail frames; adapt category vocabulary; omit SerializableAdvices unless diagnostics cross serialization boundaries. Coverage caveat: pinned by rendering snapshots across the workspace rather than in-crate tests.
