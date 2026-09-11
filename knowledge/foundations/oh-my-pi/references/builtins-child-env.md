<!-- capsule-v2 -->
# Child-process plumbing — how do utility builtins spawn helpers without inheriting the TUI's stdio?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What must a child process inherit from the SHELL rather than the host process, and how are its streams wired?

## ChildEnv + Host::run_captured
**Path/Symbol:** `crates/pi-builtins/src/host.rs:` `struct ChildEnv` (:445-449), `ChildEnv::command` (:457-465), `ChildEnv::forward_stderr` (:474-482), `Host::run_captured` (:260-287).
**Signature:** `pub fn command(&self, program) -> Command` (always `.current_dir(cwd).env_clear().envs(...).stderr(piped)`); `pub fn forward_stderr(&self, child_stderr: ChildStderr) -> JoinHandle<()>`.
**Data Shape:** `ChildEnv { cwd, env: Arc<Vec<(String,String)>>, stderr: OpenFile }`, `Clone` so it can move into worker threads and helper types that never see `Host` (e.g. `sort --compress-program` spawns from inside the temp-file abstraction).

### Decisive source
```rust
/// The host process's fd 0/1/2 belong to the TUI — a child must never
/// inherit stdio.
pub fn run_captured(&mut self, command: &mut std::process::Command) -> io::Result<ExitStatus> {
	command.stdin(Stdio::null()).stdout(Stdio::piped()).stderr(Stdio::piped());
	let mut child = command.spawn()?;
	...
	if let Some(mut out) = child.stdout.take() {
		let _ = io::copy(&mut out, &mut self.stdout);   // streams through on calling thread
	}
	let status = child.wait();                           // stderr drained on helper thread,
	if let Ok(buf) = stderr_thread.join() {              // forwarded AFTER exit in one write
		let _ = self.stderr.write_all(&buf);
	}
	status
}
```

**Flow:** child built with shell's cwd + exported env (so PATH lookup finds programs installed only for the shell) + stderr ALWAYS piped → caller wires stdin/stdout explicitly (defaults are inherited and MUST be redirected) → run_captured: stdin=null, stdout streams through live, stderr buffered on a helper thread and flushed after wait so diagnostics land before the utility reports.
**Invariant:** A child left with inherited stderr writes straight into the rendered TUI frame — the pipe is load-bearing, not an optimization. Callers stay responsible for `current_dir` + env; nothing here sets them implicitly for hand-built Commands.
**Probe:** no dedicated unit test drives `run_captured`; consumer coverage via `sort --compress-program` probe path (`sort.rs:971-993` spawns the compressor through `compress.env.command`). Deterministic anchor: `grep -c 'a child must never' crates/pi-builtins/src/host.rs` = 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "run_captured child stderr drain helper thread", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `Host.run_captured host.rs:260-287`.

## Verdict
Adopt the three-inheritance rule (cwd, exported env, duplicated stderr) plus never-inherit-stdio for any embedded-shell child spawn. Adapt to your process API; keep the post-exit stderr forwarding ordering when diagnostics must precede the utility's own result line.
