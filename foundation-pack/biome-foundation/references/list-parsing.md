<!-- capsule-v2 -->
# List parsing — how do you parse node lists and separated lists with progress guards and per-element recovery?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** list parsing is the most error-prone grammar loop (trailing separators, missing elements, recovery boundaries). What do `ParseNodeList` and `ParseSeparatedList` encode so a porter gets the loop right?

## The list-parsing seam
**Path/Symbol:** `crates/biome_parser/src/parse_lists.rs` — `ParseNodeList` (20-73), `ParseSeparatedList` (86-187); `crates/biome_parser/src/lib.rs:ParserProgress` (576-615).
**Signature:** `trait ParseNodeList { const LIST_KIND; parse_element(&mut self,p)->ParsedSyntax; is_at_list_end(&self,p)->bool; recover(&mut self,p,parsed)->RecoveryResult; parse_list(&mut self,p)->CompletedMarker }`; `trait ParseSeparatedList` adds `separating_element_kind()`, `allow_empty()`, `allow_trailing_separating_element()`, `expect_separator()`, `diagnose_missing_element()`.
**Data Shape:** both traits are `type Parser<'source>: Parser`; `ParserProgress(Option<TextSize>)` tracks the last source position.

### Decisive source
```rust
// parse_lists.rs:55-72 — ParseNodeList::parse_list
fn parse_list(&mut self, p: &mut Self::Parser<'_>) -> CompletedMarker {
    let elements = self.start_list(p);
    let mut progress = ParserProgress::default();
    while !p.at(EOF) && !self.is_at_list_end(p) {
        progress.assert_progressing(p);              // panic if no forward progress
        let parsed_element = self.parse_element(p);
        if self.recover(p, parsed_element).is_err() { break; }
    }
    self.finish_list(p, elements)
}
```
```rust
// parse_lists.rs:152-186 — ParseSeparatedList::parse_list (trailing separator + missing-element handling)
fn parse_list(&mut self, p: &mut Self::Parser<'_>) -> CompletedMarker {
    let elements = self.start_list(p); let mut progress = ParserProgress::default(); let mut first = true;
    loop {
        if (self.allow_empty() || !first) && (p.at(EOF) || self.is_at_list_end(p)) { break; }
        if first { first = false; } else {
            self.expect_separator(p);                 // adds missing-separator diagnostic if absent
            if self.allow_trailing_separating_element() && self.is_at_list_end(p) { break; }
        }
        progress.assert_progressing(p);
        let parsed_element = self.parse_element(p);
        if parsed_element.is_absent() && p.at(self.separating_element_kind()) {
            self.diagnose_missing_element(p);         // hook for "missing element before separator"
            continue;
        }
        if self.recover(p, parsed_element).is_err() { break; }
    }
    self.finish_list(p, elements)
}
```
`ParserProgress::assert_progressing` panics ("The parser is no longer progressing") if a loop iteration doesn't advance the source position — the guard that turns an infinite recovery loop into a loud failure. `expect_separator` calls `p.expect(separating_element_kind())` which emits an `expected_token` diagnostic when the separator is missing (the "missing required" empty slot). `recover` returning `Err` (Eof/AlreadyRecovered/RecoveryDisabled) breaks the loop — this is what stops list parsing at a statement/block boundary instead of spinning.
**Flow:** start a marker → loop while not at EOF/list-end → assert progress → parse one element → if absent, recover into a Bogus node (or break if recovery fails) → for separated lists, expect the separator first (with trailing-separator early-exit) and handle the missing-element-before-separator case → finish the list node.
**Invariant:** every loop iteration must advance the source position (ParserProgress guard); recovery failure must break the loop (never continue); separated lists handle trailing separators and missing elements explicitly rather than by accident.
**Probe:** the whole `crates/biome_js_parser/tests/js_test_suite/` corpus exercises list parsing (arrays, args, params, imports) with trailing-comma and error snapshots. No dedicated unit test of the traits; `ParserProgress` has no direct test either.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ParseSeparatedList parse_list ParserProgress assert_progressing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the progress-guarded loop, per-element recovery with break-on-failure, and the explicit separator/trailing/missing-element hooks; adapt `LIST_KIND`/separator kinds per grammar; omit nothing core. Coverage caveat: no dedicated unit test — pinned by the js_test_suite snapshot corpus.
