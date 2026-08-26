<!-- capsule-v2 -->
# Host contract — how do standalone CLI utilities run as in-process shell builtins without touching process-global I/O?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** What exact view of the shell must a utility builtin receive, and what does the adapter guarantee around it, so a ported `grep`/`sed` behaves like the real program inside a long-lived host process?

## The Utility trait + util() adapter
**Path/Symbol:** `crates/pi-builtins/src/host.rs:` `trait Utility` (:57-81), `struct Host` (:89-112), `async fn run_utility` (:730-803), `fn build_host` (:832-897), `fn or_null` (:901-906).
**Signature:** `trait Utility: clap::Parser + Send + Sync + 'static { const NAME: &'static str; const USAGE_ERROR: u8 = 1; fn rewrite_argv(...) -> Result<Vec<OsString>, String>; fn run(self, host: &mut Host) -> i32 }`; `pub(crate) fn util<U: Utility, SE>() -> Registration<SE>`.
**Data Shape:** `Host` is an OWNED value (streams, cwd PathBuf, exported-env HashMap, `cancel: Arc<AtomicBool>`, exit_code) snapshot from the ExecutionContext — it moves to a blocking thread; nothing borrows the shell. Public stream FIELDS (not accessors) so a utility can hold `&mut` of two at once.

### Decisive source
```rust
let parsed = match U::try_parse_from(&argv) {
	Ok(parsed) => parsed,
	Err(err) => {
		let rendered = err.to_string();
		if err.use_stderr() {                       // usage error -> stderr + USAGE_ERROR
			let _ = write!(context.stderr(), "{rendered}");
			return Ok(ExecutionResult::new(U::USAGE_ERROR));
		}
		let _ = write!(context.stdout(), "{rendered}"); // --help/--version -> stdout + success
		return Ok(ExecutionResult::success());
	},
};
...
let mut handle = tokio::task::spawn_blocking(move || { run_caught::<U>(parsed, &mut host) });
```

**Flow:** capture everything owned BEFORE first await (keeps future `Send`) → materialize `/dev/fd/<n>` process-substitution args to real fds → `rewrite_argv` → clap parse (help/version on stdout=0, usage errors on stderr=USAGE_ERROR) → `build_host` snapshots streams/cwd/exported env → `spawn_blocking(run_caught)` → select on cancel-token vs completion → exit code `(code & 0xff) as u8`.
**Invariant:** (1) Relative paths resolve against the SHELL's cwd (`host.resolve`), never the host process's — every path argument must go through it. Exported shell vars are NOT in the process environment, so `std::env::var` misses them — use `host.var`. (2) Closed fd becomes /dev/null via `or_null` so utilities see EOF/discard instead of failing. (3) Cancellation is one shared flag: adapter flips it, blocked stdin read observes the SAME Arc and returns EOF, utility unwinds cleanly flushing partial output; final code 130. (4) Panics are contained at the boundary by `run_caught` (catch_unwind → `<name>: internal error`, exit 1) with a thread-local `PANIC_SCOPE_DEPTH` guard so the native crash hook knows the panic will be caught.
**Probe:** `crates/pi-builtins/src/host.rs:1197` `line_policy_flushes_completed_lines_immediately` + :1216 `regular_file_gets_block_buffering` + :1235 `pipe_wrapped_as_file_gets_line_buffering` pin the buffering side of this contract (see stdout-writer capsule).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "run_utility spawn_blocking cancel token utility builtin", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `Host.run_captured host.rs:260-287`, `run_caught host.rs:811-828`.

## Verdict
Adopt the owned-Host snapshot + spawn_blocking + shared cancel flag + panic containment wholesale — it is what makes ~60 CLI tools safe inside one agent process. Adapt brush's `OpenFile`/ExecutionContext types to your host's descriptor table. Omit Windows MSYS drive-alias normalization unless targeting MSYS shells. Runner caveat: cargo suite blocked in this environment (stable toolchain vs workspace `portable_simd` dep); probes verified against source text at pin.
