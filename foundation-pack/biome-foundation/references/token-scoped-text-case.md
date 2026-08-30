<!-- capsule-v2 -->
# Scoped text-case policy plumbing — how does one generic enum carry Preserve/Lowercase policy through rule instances AND scoped context?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** a formatter needs per-token case policy (canonicalize `@IMPORT`, preserve author identifiers) without a per-language reimplementation of the plumbing — what is the shared trait surface and its two consumption channels?

## TextCase + FormatScopedOptions
**Path/Symbol:** kernel `crates/biome_formatter/src/token_case.rs` — `TextCase { Auto, Preserve, Lowercase }` (:12-23), `FormatRuleWithTextCase` (:29-35), ref/owned wrapper impls (:37-61), `FormatTextCaseExt::with_text_case` → `FormatWithScopedOptions` (:67-80). CSS binding `crates/biome_css_formatter/src/utils/case.rs` — `pub(crate) type CssCase = TextCase` (:33), `FormatScopedOptions<CssFormatContext, T> for CssCase` (:35-62), policy ladders `value_identifier_case`/`unknown_at_rule_name_case`/`query_feature_name_case`/`pseudo_identifier_case` (:95-185). Consumption `crates/biome_css_formatter/src/context.rs:43-45` + `crates/biome_css_formatter/src/css/value/identifier.rs:11-17` + `crates/biome_css_formatter/src/lib.rs:327-357`.
**Signature:** `fn with_text_case(self, case: TextCase) -> Self` (wrapper chain); `fn enter(&self, item: &T, context: &mut CssFormatContext) -> Option<Self>` / `fn exit(&self, restore: Option<Self>, context: &mut CssFormatContext)`; `replace_identifier_case(&mut self, case: CssCase) -> CssCase` (mem::replace returns prior).
**Data Shape:** two channels for ONE policy enum: (a) RULE-INSTANCE channel — `.format()?.with_text_case(CssCase::Preserve)` stamps the case into the `FormatCssSyntaxToken { case }` copy; (b) SCOPED-CONTEXT channel — `with_text_case` on any formatted item pushes into `CssFormatContext.identifier_case` via enter/exit RAII, read back by node rules like `FormatCssIdentifier`.

### Decisive source
```rust
// utils/case.rs:41-55 — the escape-downgrade invariant inside enter():
fn enter(&self, item: &T, context: &mut CssFormatContext) -> Self::Restore {
    debug_assert!(T::can_cast(CssSyntaxKind::CSS_IDENTIFIER),
        "CSS identifier case requires an identifier-capable node");
    let identifier = CssIdentifier::cast_ref(item.syntax())?;
    let case = if *self == Self::Lowercase && identifier_has_escape(&identifier) {
        Self::Preserve            // lowercasing escaped idents would be incomplete
    } else {
        *self
    };
    Some(context.replace_identifier_case(case))
}

// lib.rs:342-352 — rule-instance channel lowercases ONLY when it must allocate:
if self.case == CssCase::Lowercase {
    let original = token.text_trimmed();
    match original.to_ascii_lowercase_cow() {
        Cow::Borrowed(_) => self.format_trimmed_token_trivia(token, f), // verbatim path
        Cow::Owned(lowercase) =>
            write!(f, [text(&lowercase, Some(token.text_trimmed_range().start()))]),
    }
}
```
**Flow:** callsites choose policy by ownership — Lowercase for syntax-owned case-insensitive names (`@IMPORT`, `:HOVER`, CSS-wide keywords INITIAL/INHERIT/UNSET/REVERT via `value_identifier_case`), Preserve for author-owned text (custom idents `$Theme`, Sass interpolation, dashed `--x` names, `scroll-state()` contexts); Auto is NEVER selected explicitly — it's the default that debug builds AUDIT: `record_auto_identifier`/`record_auto_contextual_token` write audit events ("used an unclassified case policy") so formatter tests expose missing decisions.
**Invariant:** escaped identifiers downgrade Lowercase→Preserve at the ENTER gate because lowercasing only unescaped characters would be incomplete — the check lives in `enter`, not at print time, so BOTH channels inherit it only via the context path (direct token-rule calls bypass `enter` and rely on their own ladder choice). The lowercase print path keeps source-position mapping by emitting `text(&lowercase, Some(token.text_trimmed_range().start()))`, never a plain unmapped write.
**Probe:** kernel tests `crates/biome_formatter/src/token_case.rs:118-201`: `syntax_token_wrappers_forward_case_to_the_rule` (both wrappers), `formatted_items_apply_text_case_through_scoped_options` (enter/exit restore verified: after formatting, context case is back to Auto). Greps: `grep -nF 'Lowercase && identifier_has_escape' crates/biome_css_formatter/src/utils/case.rs` → 1 hit :48; `grep -nF 'to_ascii_lowercase_cow' crates/biome_css_formatter/src/lib.rs` → :350; `grep -nF 'record_audit_event(std::format!(' crates/biome_css_formatter/src/utils/case.rs` → :67/:80.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"TextCase"}'
# biome.crates.biome_formatter.src.token_case TextCase Enum 12-23 (+ both trait surfaces)
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"replace_identifier_case"}'
# biome.crates.biome_css_formatter.src.context.CssFormatContext Method 43-45
```

## Verdict
Adopt the dual-channel policy plumbing + escape-downgrade + debug-Audit-of-Auto pattern for any canonicalization-vs-preservation split; adapt the policy ladders (they enumerate YOUR language's ownership rules); omit the scoped-options machinery if every callsite can stamp the rule instance directly. Coverage: all three files indexed clean (`no_recorded_issue` @ 2026-08-16T00:20:04Z).
