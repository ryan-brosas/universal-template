<!-- capsule-v2 -->
# Suppression code-action emitter — where does the ignore comment land when the diagnostic spans weird trivia?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** given a diagnostic offset, which token receives the suppression comment, on which line, and what happens to existing comments around it?

## The SuppressionAction seam
**Path/Symbol:** `crates/biome_analyze/src/suppression_action.rs` — trait (:7-112), `get_token_from_offset` (:54-72), `ApplySuppression` (:115-122), `new_trivia_for_top_suppression_with_comments` (:125-153), `new_trivia_for_top_suppression` (:156-176).
**Signature:** `fn inline_suppression(&self, payload: SuppressionCommentEmitterPayload<L>)` with payload `{ token_offset: TokenAtOffset<SyntaxToken<L>>, mutation: &mut BatchMutation<L>, suppression_text, diagnostic_text_range, suppression_reason }`.
**Data Shape:** `ApplySuppression { token_has_trailing_comments: bool, token_to_apply_suppression: SyntaxToken<L>, should_insert_leading_newline: bool }` — the language impl's `find_token_for_inline_suppression` decides line placement (e.g. JS walks back to a token whose leading trivia has a newline).

### Decisive source
```rust
// suppression_action.rs:59-71 — BETWEEN-tokens tie-break prefers the RIGHT token
// only when it starts exactly at the diagnostic start (doc-comment example: JSX
// `><img /> {/* comment */}` — right token belongs to the erroring node):
match token_at_offset {
    TokenAtOffset::None => None,
    TokenAtOffset::Single(token) => Some(token),
    TokenAtOffset::Between(left_token, right_token) => {
        let chosen_token =
            if right_token.text_range().start() == diagnostic_text_range.start() {
                right_token
            } else {
                left_token
            };
        Some(chosen_token)
    }
}
```
**Flow:** inline path: resolve token → language finds the anchor token (`find_token_for_inline_suppression`) → `apply_inline_suppression` mutates the batch. Top-level path: if the token's leading trivia HAS comments, insert the new comment AFTER the last comment block preceded by a newline (`new_trivia_for_top_suppression_with_comments`: after_comment latch + one-shot insertion flag); otherwise PREPEND `<comment>\n` before all existing leading trivia; rebuild the token detached with `SyntaxToken::new_detached(kind, text, new_trivia, [])` re-attaching original trailing pieces and `replace_token_discard_trivia`.
**Invariant:** top-level comments never jump above existing ones (they append after them) — porters who prepend blindly reorder user comments; the between-offset tie-break is diagnostic-start-anchored, not arbitrary-left; silent no-op when no anchor token exists (Option chain, never panic).
**Probe:** upstream `crates/biome_js_analyze/tests/suppression/` fixture suites pin emitted comment positions per syntax shape (the JS `find_token_for_inline_suppression` behavior lives in js_analyze's SuppressionAction impl — its fixtures are the direct tests); in-crate there are no #[test]s — the trivia builders' correctness rides the fixture snapshots.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SuppressionAction ApplySuppression apply_top_level_suppression", limit: 10, fields: ["signature", "name", "file"] });
// get_token_from_offset suppression_action.rs 54-72; new_trivia pair 125-176 (line-exact)
```

## Verdict
Adopt the token-resolution ladder (none/single/between-with-diagnostic-start tie-break), the after-existing-comments insertion rule for top-level suppressions, and fail-silent Option flow; adapt the anchor-token search per language grammar; omit the specific TriviaPiece reconstruction if your tree API can splice trivia directly. Coverage caveat: pinned by js_analyze suppression fixtures, not by this crate's own tests.
