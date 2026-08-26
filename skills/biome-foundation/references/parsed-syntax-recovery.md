<!-- capsule-v2 -->
# ParsedSyntax + error recovery — how do you make optional/absent grammar results explicit and recover from bad tokens into Bogus nodes?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome` (full mode, 141,682 nodes / 644,530 edges, generation 2026-08-16). **Question:** parse rules must signal "absent" without eating tokens or adding errors, and must recover from unexpected tokens into a `Bogus*` node. What is the `ParsedSyntax` contract and the `ParseRecovery` machinery?

## The optional-syntax + recovery seam
**Path/Symbol:** `crates/biome_parser/src/parsed_syntax.rs:ParsedSyntax` (full, 330L); `crates/biome_parser/src/parse_recovery.rs` (`RecoveryError` 7-46, `ParseRecoveryTokenSet` 53-114,, `ParseRecovery` trait 118-153).
**Signature:** `enum ParsedSyntax { Absent, Present(CompletedMarker) }` with `ok/and_then/or_else/map/unwrap/unwrap_or/or_add_diagnostic/precede_or_add_diagnostic/or_recover_with_token_set/or_recover`; `ParseRecoveryTokenSet::recover(p) -> RecoveryResult`; `RecoveryResult = Result<CompletedMarker, RecoveryError>`.
**Data Shape:** `ParsedSyntax` is `#[must_use]` (Absent must be handled). `RecoveryError` is `Eof | AlreadyRecovered | RecoveryDisabled`. `ParseRecoveryTokenSet{ node_kind, recovery_set: TokenSet, line_break: bool }` with `enable_recovery_on_line_break()`.

### Decisive source
```rust
// parsed_syntax.rs:13-27 — the rule contract (verbatim)
// * A parse rule must return Present if it can parse a node or at least parts of it.
// * A parse rule must return Absent if the expected node isn't present (e.g. first token missing).
// * A parse rule must not eat any tokens when it returns Absent.
// * A parse rule must not add any errors when it returns Absent.
```
```rust
// parse_recovery.rs:82-105 — eat unexpected tokens into a Bogus node until a safe token
pub fn recover<P: Parser<Kind=K>>(&self, p: &mut P) -> RecoveryResult {
    if p.at(P::Kind::EOF) { return Err(RecoveryError::Eof); }
    if self.is_at_recovered(p) { return Err(RecoveryError::AlreadyRecovered); }
    if p.is_speculative_parsing() { return Err(RecoveryError::RecoveryDisabled); }
    let m = p.start();
    while !(self.is_at_recovered(p) || p.at(P::Kind::EOF)) { p.bump_any(); }
    Ok(m.complete(p, self.node_kind))
}
```
`AlreadyRecovered` exists because a completed marker wrapping no tokens is invalid AND because recovery inside a while-loop would infinite-loop (list parsing recovers at `;`/`}` boundaries — see parse_lists.md). `RecoveryDisabled` fires during speculative parsing: error-recovery would make a speculative parse look like it succeeded when it only skipped tokens (the `(a,b,c)...` arrow-vs-paren case). `ParsedSyntax::or_recover_with_token_set` wraps `recover` and adds a diagnostic at the recovered range (or current range on failure).
**Flow:** a parse rule returns `ParsedSyntax`; callers chain `.or_recover_with_token_set(p, &recovery, error_builder)` → if `Present`, pass through; if `Absent`, `recover` eats tokens into a `Bogus*` node until a safe token/EOF/line-break, then a diagnostic is added. `precede_or_add_diagnostic` lets a rule start a wrapper node around an already-parsed or missing element.
**Invariant:** Absent ⇒ no tokens eaten and no errors added (so speculative re-parse and list loops stay correct); recovery must never produce an empty node or loop forever (the two error variants encode exactly those two failure modes); recovery is disabled during speculative parsing.
**Probe:** `crates/biome_js_parser/tests/js_test_suite/error/` snapshot corpus pins recovery shapes (Bogus nodes + diagnostics); `crates/biome_test_utils/src/lib.rs:has_bogus_nodes_or_empty_slots` (819) asserts ok-cases contain no bogus/missing nodes. No direct unit test of `ParsedSyntax`/`ParseRecoveryTokenSet`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "ParsedSyntax or_recover_with_token_set ParseRecoveryTokenSet recover", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the explicit `Present/Absent` return contract (no tokens/errors on Absent), the `Bogus*`-node recovery with Eof/AlreadyRecovered/RecoveryDisabled errors, and the speculative-parse disable; adapt recovery token sets per grammar; omit nothing core. Coverage caveat: no dedicated unit test — pinned by the js_test_suite error snapshots + `has_bogus_nodes_or_empty_slots`.
