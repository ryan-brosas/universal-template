<!-- capsule-v2 -->
# Cross-platform process snapshot — one ProcInfo contract over /proc, proc_pidinfo, and Toolhelp

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What identity guarantees must a process-table entry carry so signalling never hits a recycled PID?

## ProcInfo per platform
**Path/Symbol:** `crates/pi-builtins/src/proc_snapshot.rs:` linux mod (:44-352), macos mod (:353-654), windows mod (:655-1081), shared `sanitize_process_command` (:31-42), re-export :1084.
**Signature:** identical accessor set per platform: `pid/ppid/args/group_id/session_id/real_user_id/effective_user_id/real_group_id/effective_group_id/terminal_id/terminal_group_id/priority/flags/minor_faults/major_faults/wchan/state/start_time/age/match_name/command_name/status/signal/cpu_time/resident_bytes/virtual_bytes/thread_count/nice`.
**Data Shape:** Linux: `/proc/<pid>/stat` parsed by FIRST `(` to LAST `)` (comm may contain spaces/parens) + positional fields (state=0, ppid=1 … start_time=19); uid/gid from `/proc/<pid>/status` `Uid:`/`Gid:` lines. macOS: `proc_pidinfo(PROC_PIDTBSDINFO)` + optional TASKINFO; args via `sysctl(CTL_KERN, KERN_PROCARGS2=49, pid)` — argc prefix, skip exe path NULs + padding zeros, then NUL-terminated strings up to argc. Windows: two Toolhelp snapshots bracketing an OpenProcess(SYNCHRONIZE) map pid→handle+creation-time.

### Decisive source
```rust
// linux: identity = start-time match; zombies are NOT Running.
pub fn status(&self) -> ProcessStatus {
	match read_stat(self.pid) {
		Some(stat) if stat.start_time == self.stat.start_time && stat.state != 'Z' =>
			ProcessStatus::Running,
		_ => ProcessStatus::Exited,
	}
}
// linux signal: pidfd_send_signal after identity re-check (defeats PID recycling).
let Some(pidfd) = open_pidfd(self.pid) else { return false };
if read_stat(self.pid).is_none_or(|stat| stat.start_time != self.stat.start_time) { return false }
libc::syscall(libc::SYS_pidfd_send_signal, pidfd.as_raw_fd(), signal, null::<siginfo_t>(), 0)
```

**Flow:** `ProcInfo::all()` walks the table once per command → consumers filter/sort by `(start_time, pid)` → any SIGNAL path re-verifies start-time identity immediately before delivery (linux via pidfd_open+stat compare; macOS live bsdinfo compare; Windows fresh OpenProcess + creation FILETIME compare, then TerminateProcess).
**Invariant:** (1) Start time is the identity token on ALL three platforms and is monotonic, so "larger = younger". (2) Signal 0 is the liveness probe and uses stat presence only (no pidfd needed). (3) `sanitize_process_command` maps control chars (incl. embedded newlines) to spaces because ps/top render verbatim into tables. (4) Option-returning accessors return None where a platform has no concept (Windows: no groups/sessions/uids/faults) — consumers treat None as "unavailable", not "mismatch".
**Probe:** `proc_snapshot.rs:1222` `a_recycled_parent_pid_is_not_followed`, :1390 `chain_stays_in_inline_storage` (see host-processes capsule); deterministic anchor `grep -c 'SYS_pidfd_send_signal' crates/pi-builtins/src/proc_snapshot.rs` = 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "ProcInfo all process table snapshot start_time", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `a_recycled_parent...` :1222-1231 rank-1 for recycled-parent query.

## Verdict
Adopt the accessor contract + start-time identity discipline for any cross-platform process tooling. Adapt the per-platform readers to your OS set; omit KERN_PROCARGS2 parsing if you don't need macOS argv. The pidfd-then-compare delivery order is non-negotiable in ports.
