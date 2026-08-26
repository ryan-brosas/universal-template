<!-- capsule-v2 -->
# xargs command-size limiters — ARG_MAX budget, exit-code ladder, limiter chain

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils findutils 0.8.0 port); Codebase Memory `oh-my-pi`. **Question:** How is the per-invocation argv budget computed, and what does each failure exit code mean?

## CommandSizeLimiter chain
**Path/Symbol:** `crates/pi-builtins/src/xargs.rs:` `trait CommandSizeLimiter` (:82-89), `MaxCharsCommandSizeLimiter::new_system` (:172-185), `MaxArgs` (:209-241), `MaxLines` (:243+), execute/exit mapping tests (:1403+).
**Signature:** `fn try_arg(&mut self, arg: Argument, cursor: LimiterCursor) -> Result<Argument, ExhaustedCommandSpace>` — chainable; each limiter counts only NON-initial args (`arg.kind != ArgumentKind::Initial`).
**Data Shape:** unix budget = `_SC_ARG_MAX − 2048 (POSIX headroom for child env) − Σ(len(var)+len(val)+1 over env)`; Windows = 32 767 (CreateProcess docs). Per-arg cost = byte length + 1 (NUL/space).

### Decisive source
```rust
// POSIX requires that we leave 2048 bytes of space so that the child processes
// can have room to set their own environment variables.
const ARG_HEADROOM: usize = 2048;
let arg_max = unsafe { libc::sysconf(libc::_SC_ARG_MAX) } as usize;
let env_size: usize = env.iter()
	.map(|(var, value)| count_osstr_chars_for_exec(var) + count_osstr_chars_for_exec(value))
	.sum();
Self::new(arg_max - ARG_HEADROOM - env_size)
```

**Flow:** input items accumulate into a builder while every limiter accepts → exhaustion closes the current invocation and starts a new one → `-n/-s/-l` add their limiters; `-0` switches parsing to NUL records preserving spaces/newlines → run each batch via ChildEnv.
**Invariant:** Exit codes are a taxonomy, not errors: any child failed = 123; child missing = 127; child exists but unexecutable = 126; child exited 255 = 124; child KILLED BY SIGNAL = 125; command+env too large even alone = diagnostic + 1. Empty input without `-r` still runs the default `echo` once.
**Probe:** direct tests pin every exit: `xargs.rs:1418 failing_child_yields_123`, :1425 `missing_command_yields_127`, :1433 `unexecutable_command_yields_126`, :1442 `exit_255_child_yields_124`, :1450 `signalled_child_yields_125`, :1457 `no_run_if_empty_skips_command`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "xargs CommandSizeLimiter try_arg exhausted", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `CommandSizeLimiter xargs.rs:82-89`.

## Verdict
Adopt the composable limiter trait + exact budget formula (the 2048 headroom and live env sizing are the parts ports get wrong). Adapt Argument plumbing; keep the six-way exit taxonomy verbatim — scripts depend on it.
