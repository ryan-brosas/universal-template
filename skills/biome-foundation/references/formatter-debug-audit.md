<!-- capsule-v2 -->
# Debug-only format audit — how do you catch "no explicit formatter decision" bugs at runtime without paying anything in release?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** speculative formatting (best_fitting, memoized inspection) can record provisional decisions — what is the snapshot/restore/audit trio that turns unresolved decisions into loud panics in debug builds only?

## PrintedTokens + FormatAudit snapshot discipline
**Path/Symbol:** `crates/biome_formatter/src/printed_tokens.rs` (99L) — `PrintedTokens { offsets: IndexSet<TextSize>, disabled }` (:9-13) exploiting "no two tokens can have an overlapping range" so an IndexSet of START OFFSETS replaces an interval tree; `track_token` (:21-39: disabled short-circuit → empty-range skip → `insert` returning false = PANIC "You tried to print the token … twice … memoize the token"); `assert_all_tracked` (:74-97: clones the set, shift_removes every descendant token's start — missing = "token has not been seen by the formatter … Use `format_replaced`/`format_removed`", leftovers = "tracked offset … doesn't match any token of … Have you passed a token from another tree?"). `crates/biome_formatter/src/format_audit.rs` (43L) — event Vec + len-snapshot truncate. State plumbing in lib.rs: `FormatState` (:2283-2452, RefCell ONLY because debug fields exist; release builds keep Formatter fully immutable), paired methods compiled to no-ops via `#[cfg(not(debug_assertions))]` stubs (:track_token :2356/:2360, record_audit_event :2370/:2375, set_token_tracking_disabled :2387/:2396, assert_formatted_all_tokens :2411/:2415, assert_no_audit_events :2425/:2429), `snapshot()`/`restore_snapshot()` (:2434-2452).
**Signature:** `pub fn track_token<L: Language>(&mut self, token: &SyntaxToken<L>)` (+ cfg-eliminated twin); `pub(crate) fn restore(&mut self, snapshot: PrintedTokensSnapshot)` truncates the IndexSet to the snapshotted length AND restores the disabled flag.
**Data Shape:** two independent ledgers with one snapshot shape each (`{len}` / `{len, disabled}`). Speculative writes append; restore rolls back EXACTLY what speculation appended — earlier events/tokens survive.

### Decisive source
```rust
// format_audit.rs test-pinned semantics (lib.rs:3067-3074):
let mut state = FormatState::new(SimpleFormatContext::default());
state.record_audit_event("persistent formatter decision");
let snapshot = state.snapshot();
state.record_audit_event("speculative formatter decision");
state.restore_snapshot(snapshot);
state.assert_no_audit_events();   // panics: "persistent formatter decision" SURVIVES
```
```rust
// printed_tokens.rs:33-38 — duplicate print = panic, remedy named:
if !self.offsets.insert(range.start()) {
    panic!("You tried to print the token '{token:?}' twice, and this is not valid.\
\nYou may need to memoize the token if you are writing it to multiple buffers at the same time.")
}
```
**Flow:** every printed token calls `track_token`; every rule that speculates wraps its window in `snapshot()/restore_snapshot()`; entry pipeline ends with `assert_formatted_all_tokens(root)` + `assert_no_audit_events()` — together they prove the output covers every input token exactly once AND no unresolved decision leaked. The HTML embedded path pre-tracks tokens precisely to satisfy this ledger across phases (see formatter-embedded-two-phase). Audit events are recorded e.g. by best-fitting variants whose decision the printer later resolves.
**Invariant:** release builds compile ALL of this away — the no-op stubs mean a porter may implement it as pure debug asserts, but must NOT move the checks behind a feature flag that production CI skips, or double-print/token-drop regressions ship silently. Restore must be truncate-to-snapshot-len (not clear): earlier legitimate events persist.
**Probe:** `grep -c 'shift_remove' crates/biome_formatter/src/printed_tokens.rs` → 1; `grep -n 'You tried to print the token' crates/biome_formatter/src/printed_tokens.rs` → :39; `grep -n 'tracked offset {offset:?}' …` → :95; `grep -n 'fn format_state_restore_preserves_earlier_audit_events' crates/biome_formatter/src/lib.rs` → :3067 (`#[should_panic(expected = "persistent formatter decision")]` :3066); `format_reports_audit_events` :3042 + `#[should_panic(expected = "formatter audit failed")]` pair :3030/:3041.
**Retrieve:**
```
codebase-memory-mcp cli search_graph '{"project":"biome","name_pattern":"PrintedTokens"}'
# PrintedTokens Struct 9-13 / PrintedTokensSnapshot Struct 16-19
```

## Verdict
Adopt the dual-ledger + len-snapshot design for any IR printer with speculation; adapt panics to your host's assertion mechanism (they fire only under debug); omit FormatAudit if you have no decision-recording machinery (but keep token coverage). Coverage: both files fully indexed no_recorded_issue @ generation 2026-08-16T00:20:04Z.
