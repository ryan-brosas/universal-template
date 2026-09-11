<!-- capsule-v2 -->
# timeout builtin — configured-signal delivery via SpawnObserver, GNU exit ladder

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How do you deliver a CONFIGURED signal (not just SIGKILL) to a command run inside the same process, and what status does each ending report?

## SpawnRecorder + select ladder
**Path/Symbol:** `crates/pi-builtins/src/timeout.rs:` `struct SpawnRecorder(Mutex<Vec<(i32, Option<i32>)>>)` (:94-124), `parse_signal` (:128-136), `execute` select ladder (:253-326), status synthesis (:328-350).
**Signature:** `impl SpawnObserver for SpawnRecorder { fn on_spawn(&self, pid: i32, pgid: Option<i32>) }`; `fn signal(&self, signal: TrapSignal, group: bool) -> bool`.
**Data Shape:** `EXIT_TIMED_OUT=124`, `EXIT_KILLED=137` (128+SIGKILL), usage failures `125`; `--foreground` → `ProcessGroupPolicy::SameProcessGroup` + signals direct children only; default NewProcessGroup → signal `-pgid`.

### Decisive source
```rust
tokio::select! {
	result = &mut run_future => return result,
	() = &mut outer_cancelled => { child_cancel.cancel(); return Ok(Interrupted.into()); },
	() = &mut deadline => {},                       // zero duration never fires (pending)
}
let signalled = spawns.signal(signal, !args.foreground);
if !signalled {
	// The operand ran in-process (a builtin) or the child is already gone;
	// cancellation is the only remaining lever (degrades external children to SIGKILL).
	child_cancel.cancel();
}
```

**Flow:** record every spawned child's pid/pgid through the shell's SpawnObserver hook → on expiry deliver configured signal (group unless --foreground) → if nothing was signalled fall back to child_cancel (brush tokens only SIGKILL) → wait; with `-k` escalate SIGKILL after kill_after and bound reaping by 2 s so a wedged in-process operand can't hang forever → status: preserve-status ? (signalled ? child : 128+N or 137 deterministic for cancel-fallback) : killed ? 137 : 124.
**Invariant:** (1) The observer exists because brush cancellation can ONLY SIGKILL — without pid/pgid capture GNU's "send TERM" is impossible. (2) After cancel-fallback the inner shell may surface Interrupted instead of the operand result; reap() treats un-signalled Interrupted as expected retirement (`Ok(None)`), not a fault. (3) Signal diagnostics render like GNU: `TERM` not `SIGTERM`.
**Probe:** direct tests pin endings: `timeout.rs:460 command_finishing_inside_limit_returns_its_status`, :467 `command_exceeding_limit_is_cancelled_with_timeout_status`, :559 `zero_duration_disables_the_timeout`, :569 `preserve_status_reports_death_by_the_timeout_signal`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "SpawnRecorder signal process group timeout", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `SpawnRecorder.signal timeout.rs:107-123`.

## Verdict
Adopt spawn-observation + group signalling + the 124/125/126/127/137 status ladder for any in-process timeout. Adapt ProcessGroupPolicy to your job control; keep the 2 s SIGKILL reaping bound — it is what makes timeout safe against wedged builtins.
