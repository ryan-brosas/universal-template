<!-- capsule-v2 -->
# find cancellation plumbing — walker-level Interrupted as the abort channel

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils findutils port); Codebase Memory `oh-my-pi`. **Question:** How does a 5.4k-line recursive expression evaluator stop promptly on shell abort without corrupting traversal state?

## cancel flag → io::Error bridge
**Path/Symbol:** `crates/pi-builtins/src/find.rs:` cancel acquisition :4816, closure check :4818-4822.
**Signature:** `let cancel = host.cancel_flag();` then inside the walk callback: `if cancel.load(Relaxed) { Err(io::Error::new(ErrorKind::Interrupted, "cancelled")) }`.
**Data Shape:** The callback's error type is io::Error; Interrupted is the sentinel distinguishing user abort from real fs errors (real errors report per-path and continue per POSIX find semantics).

### Decisive source
```rust
let cancel = host.cancel_flag();
...
if cancel.load(std::sync::atomic::Ordering::Relaxed) {
	Err(io::Error::new(io::ErrorKind::Interrupted, "cancelled"))
} else { ... }
```

**Flow:** every visited node consults the flag → on set, the callback errors with Interrupted which unwinds the walker (no partial-directory state leaks — walkers treat error as stop-and-propagate) → run() maps Interrupted to silent exit 130-equivalent while other errors follow GNU find's diagnostic-per-path + final exit 1.
**Invariant:** (1) Cancellation rides the EXISTING error channel rather than a side channel — no walker API changes needed, and cleanup runs through normal drop paths. (2) The flag is polled per ENTRY, not per directory: deep single directories still check between children. (3) Distinguishing Interrupted from other errors at the top is what keeps `find` from printing a spurious diagnostic on abort.
**Probe:** deterministic anchors: `grep -c 'ErrorKind::Interrupted' crates/pi-builtins/src/find.rs` ≥ 1; direct-test coverage via crate tests (runner blocked this environment).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "find cancel interrupted walker callback", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (find.rs:4816-4822).

## Verdict
Adopt error-channel cancellation with an Interrupted sentinel for long-running traversals inside cancellable hosts. Adapt error taxonomy; keep per-entry polling and silent-abort mapping.
