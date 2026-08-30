<!-- capsule-v2 -->
# JsParser instantiation — what does the concrete parser add over the language-agnostic Parser trait?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How is the generic event-parser specialized for one language, and where do keyword/unicode-escape diagnostics belong?

## JsParser + do_bump_with_context
**Path/Symbol:** `crates/biome_js_parser/src/parser.rs:JsParser` (:31-148), trait impl (:151-208), `JsParserCheckpoint` (:210-214); in-file tests (:216-262).
**Signature:** `pub struct JsParser<'source> { state: JsParserState, source_type: JsFileSource, context: ParserContext<JsSyntaxKind>, source: JsTokenSource<'source>, options: JsParserOptions }`
**Data Shape:** Composition, not inheritance: generic event log (`ParserContext`) + language token source + language state + file-type config. `finish()` returns `(Vec<Event<JsSyntaxKind>>, Vec<Trivia>, Vec<ParseDiagnostic>)`.

### Decisive source
```rust
fn do_bump_with_context(&mut self, kind: Self::Kind, context: <Self::Source as BumpWithContext>::Context) {
    let kind = if kind.is_keyword() && self.source().has_unicode_escape() {
        self.error(self.err_builder(
            format!("'{}' keyword cannot contain escape character.", kind.to_string()...),
            self.cur_range(),
        ));
        JsSyntaxKind::ERROR_TOKEN          // bump proceeds as an ERROR_TOKEN
    } else { kind };
    let end = self.cur_range().end();
    self.context_mut().push_token(kind, end);
    if self.context().is_skipping() {
        self.source_mut().skip_as_trivia_with_context(context);
    } else {
        self.source_mut().bump_with_context(context);
    }
}
```

**Flow:** `new()` builds state from `JsFileSource` (module ⇒ strict from birth; `.d.ts` ⇒ ambient) → productions call the `Parser` trait surface → every token push funnels through `do_bump_with_context`, which (a) downgrades escaped keywords to ERROR_TOKEN with a diagnostic *before* pushing, and (b) honors the skipping flag by routing to skip-as-trivia. `finish()` merges source (lexer) diagnostics with parse diagnostics via `merge_diagnostics`.
**Invariant:** The escape check must happen at bump time (not lex time) because only the grammar knows which tokens are being consumed as keywords. Marker discipline is enforced at runtime in debug builds: dropping an un-completed/un-abandoned Marker panics ("Marker must either be `completed` or `abandoned`...") — pinned by three unit tests in this same file.
**Probe:** `crates/biome_js_parser/src/parser.rs::tests::uncompleted_markers_panic / completed_marker_doesnt_panic / abandoned_marker_doesnt_panic` (direct #[test]s) plus `js_test_suite/ok/js/arrow_escaped_async.js`-style corpora for `\u0061sync`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "JsParser do_bump_with_context unicode escape keyword", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt composition-over-trait-object parser cores and the bump-time keyword-escape gate; adapt kinds/options; omit the JS-specific strict-from-module bootstrap if your language has no script/module split.
