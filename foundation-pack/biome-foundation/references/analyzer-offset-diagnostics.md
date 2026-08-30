<!-- capsule-v2 -->
# AnalyzerDiagnostic offset shim — how do diagnostics written against an embedded snippet get repositioned into the host document?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Vue/Svelte/Astro files are analyzed as embedded snippets — how does one TextSize offset shift the span, every advice frame, and code suggestions without rewriting each producer?

## The offset seam
**Path/Symbol:** `crates/biome_analyze/src/diagnostics.rs` — `AnalyzerDiagnostic` (:19-27), `DiagnosticKind::{Rule,Raw}` (:39-45), `location()` (:84-100), `advices()` OffsetVisitor (:102-147), `add_diagnostic_offset` (:185-195), `add_code_suggestion` FIXABLE tagging (:166-181); `AnalyzerSuppressionDiagnostic` builder (:202-275); `RuleError::{ReplacedRootWithNonRootError, ConflictingRuleFixesError}` (:294-374).
**Signature:** `pub fn add_diagnostic_offset(&mut self, offset: TextSize)`; `pub fn add_code_suggestion(mut self, suggestion: CodeSuggestionAdvice<MarkupBuf>) -> Self`.
**Data Shape:** `kind: DiagnosticKind` (Rule(Box<RuleDiagnostic>) | Raw(Error)) + `code_suggestion_list: Vec<CodeSuggestionAdvice<MarkupBuf>>` + `offset: Option<TextSize>` — suggestions live OUTSIDE the kind so both variants share them.

### Decisive source
```rust
// diagnostics.rs:107-133 — Raw advices get a WRAPPING visitor so EVERY recorded
// frame shifts, not just the top-level location:
struct OffsetVisitor<'a> { inner: &'a mut dyn Visit, offset: TextSize }
impl<'a> Visit for OffsetVisitor<'a> {
    fn record_frame(&mut self, location: Location<'_>) -> std::io::Result<()> {
        if let Some(span) = location.span {
            let new_span = span.add(self.offset);
            let offset_location = Location::builder()
                .span(&new_span)
                .resource(&location.resource)
                .source_code(&location.source_code)
                .build();
            self.inner.record_frame(offset_location)
        } else { self.inner.record_frame(location) }
    }
}
```
**Flow:** Rule path stores the offset on the inner diagnostic too (`set_advice_offset` shifts Detail frames AND parent_advices via `SerializableAdvices::offset_by`, rule.rs:1670-1675) AND keeps it in `self.offset` for `location()` (span-only add, guarded by `location.span.is_some()`). Adding any code suggestion flips tags to `DiagnosticTags::FIXABLE` in BOTH variants (:168-177). Suppression diagnostics are a separate Warning-severity derive-built type with `note(msg, range)` / `hint(msg)` advice pairs and four constructors naming unknown rule/group/action categories. The two `RuleError`s are the file-level failure contract: replacing the root with a non-root node, or rules whose fixes loop forever (`ConflictingRuleFixesError`) — both render "An internal error occurred when analyzing this file… likely a bug in Biome" with category internalError/panic.
**Invariant:** offsets apply to SPANS only (resource/source-code untouched); Rule-kind producers already see shifted detail ranges after set_advice_offset while Raw needs the visitor wrapper — porting only one half double-shifts or misses frames; suggestions are appended at PRINT time from the shared list.
**Probe:** upstream embedded-language suites (Vue/Svelte analyze specs under biome_html/js_analyze tests) exercise the offset path end-to-end; no in-crate #[test] targets AnalyzerDiagnostic directly — the Diagnostic impl branches above are the pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "AnalyzerDiagnostic add_diagnostic_offset DiagnosticKind", limit: 10, fields: ["signature", "name", "file"] });
// add_diagnostic_offset diagnostics.rs 185-195; location() 84-100 (line-exact)
```

## Verdict
Adopt the two-kind wrapper with shared suggestion list, the wrap-the-visitor trick for Raw advices, FIXABLE-on-suggestion tagging, and the two named file-level failure modes; adapt the severity defaults; omit the derive-macro suppression-diagnostic scaffolding if your diagnostics are hand-built. Coverage caveat: exercised by embedded-language fixture suites rather than direct unit tests.
