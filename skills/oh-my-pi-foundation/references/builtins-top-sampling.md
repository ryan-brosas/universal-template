<!-- capsule-v2 -->
# top CPU% sampling — start-time-guarded deltas over snapshot pairs

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How is per-process CPU percent computed across refresh intervals without misattributing time to a recycled PID?

## sample loop
**Path/Symbol:** `crates/pi-builtins/src/top.rs:` execute loop (:234-345), delta math (:278-296), `sanitize_process_command` use (:298-307), BrokenPipe-as-success (:324-329).
**Signature:** `previous: HashMap<i32, (u64 /*start_time*/, Duration /*cpu_time*/)>`; `cpu_percent = 100.0 × Δcpu_time / Δwall` (0.0 on first sample or zero elapsed).
**Data Shape:** `next_previous` built fresh each iteration and swapped at the END — a process absent this cycle simply drops out; delay validated `0 ≤ delay ≤ Duration::MAX`, finite.

### Decisive source
```rust
let cpu_percent = cpu_time.and_then(|current|
	previous.get(&process.pid())
		.filter(|(previous_start, _)| *previous_start == start_time)   // identity guard
		.map(|(_, old)| current.saturating_sub(*old)))
	.map_or(0.0, |delta| if elapsed.is_zero() { 0.0 }
		else { 100.0 * delta.as_secs_f64() / elapsed.as_secs_f64() });
if let Some(cpu_time) = cpu_time {
	next_previous.insert(process.pid(), (start_time, cpu_time));
}
```

**Flow:** per interval: snapshot all → filter by pid set / user (real OR effective) → compute guarded delta vs previous map → build rows (effective user preferred, sanitized command full-or-comm) → sort by chosen key → render batch snapshot (plain text for pipes/files) → write; BrokenPipe from the consumer ⇒ exit SUCCESS (a piped `top -n 1 | head` must not error) → swap maps, sleep under cancel-select.
**Invariant:** The start_time filter is the PID-recycling defense: without it a new process reusing a pid inherits the old process's accumulated cpu_time, producing a garbage first-interval spike. First sample reports 0.0 rather than lifetime-average — matching top's convention.
**Probe:** deterministic anchors: `grep -c 'previous_start' crates/pi-builtins/src/top.rs` = 1 (the identity filter at :284); `grep -c 'BrokenPipe' crates/pi-builtins/src/top.rs` ≥ 1. Runner blocked this environment (stable toolchain); behavior pinned by source reading at pin.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "top cpu percent previous snapshot delay", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (top.rs:281-286).

## Verdict
Adopt the start-time-keyed delta map + zero-first-sample + BrokenPipe-success contract for any sampling monitor. Adapt rendering freely; keep the identity guard.
