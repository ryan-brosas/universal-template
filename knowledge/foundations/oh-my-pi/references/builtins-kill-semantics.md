<!-- capsule-v2 -->
# kill builtin — signal grammar, exit-status round-trip, and kill(2) target semantics

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** Which `kill` argument spellings must parse, what does `kill -l 137` print, and which targets are refused?

## KillSignal + printed_signal + blocks_target
**Path/Symbol:** `crates/pi-builtins/src/kill.rs:` `enum KillSignal` (:606-628), `pub(crate) fn signal_number` (:638-655), `fn blocks_target` (:418-426), `fn printed_signal` (:461-480); ancestor resolution `HostProcesses::resolve` at :136.
**Signature:** `fn signal_number(value: &str) -> Option<i32>` (shared with pkill `-SIGNAL`); `fn blocks_target(host: &HostProcesses, target: i32) -> bool`.
**Data Shape:** Number range per platform: linux `0..=SIGRTMAX`, macos `0..=31`, other `0..=64`. `KillSignal::Probe` = the number 0.

### Decisive source
```rust
// bash also maps the exit status of a signal-killed process back to its signal:
// `kill -l 137` prints `KILL` (137 = 128 + 9), while an unmappable value like
// 128 or 265 keeps its own diagnostic.
let signal = TrapSignal::try_from(number).or_else(|err| {
	if number > 128 { TrapSignal::try_from(number - 128).map_err(|_| err) } else { Err(err) }
})?;
```
```rust
/// `target` follows kill(2): positive = pid, `0` = caller's own group,
/// `-1` = every process the caller may signal, negative = group `-target`.
/// The caller's own group needs no special case — it is in host.pgids by construction.
if target == -1 || target == 0 { return true; }
match target.checked_neg() {
	Some(pgid) if pgid > 0 => host.pgids.contains(&pgid),
	_ => host.pids.contains(&target),
}
```

**Flow:** argv pre-pass splits ATTACHED signal values (`-9`, `-nTERM`-style clusters keep `SIG`-prefixed specs whole) → operands after `--` never parsed as signals → signalling resolves `HostProcesses` ONCE for the whole operand loop → each delivery refused when target pid or its pgid is in the protected chain ("refusing to signal the shell process") → `-l` listing maps numbers⇄names with the 128+N round-trip.
**Invariant:** `checked_neg` on i32::MIN must not panic — negation failure falls into the pid branch. Refusal is per-operand (continue), not command-abort. Signal-name parsing accepts optional SIG/sig prefix any case; shell-only "signals" (EXIT/DEBUG/ERR) are rejected at delivery sites (`parse_signal` in timeout keeps only `TrapSignal::Signal(_)`).
**Probe:** direct tests pin the grammar: `kill.rs:545 sig_prefixed_spec_stays_whole`, :562 `attached_list_operand_splits`, :575 `rewrite_leaves_operand_region_alone`, :595 `list_maps_exit_statuses_above_128`. Deterministic anchor: `grep -c 'fn blocks_target' crates/pi-builtins/src/kill.rs` = 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "signal_number KillSignal probe SIG prefix", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 (verified via sibling query): `blocks_target kill.rs:418-426` present in graph.

## Verdict
Adopt the 128+N status mapping, attached-value cluster splitting, and kill(2) target classification with chain-based refusal. Adapt TrapSignal to your platform's signal table. Omit realtime-signal ranges beyond your OS max.
