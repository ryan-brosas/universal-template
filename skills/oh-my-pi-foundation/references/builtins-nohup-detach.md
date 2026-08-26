<!-- capsule-v2 -->
# nohup as transparent background wrapper — how does a server survive the shell's kill-on-drop teardown?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** Why does this nohup intentionally shadow the system binary, and what does foreground vs background invocation do differently?

## NohupCommand + registration
**Path/Symbol:** `crates/pi-builtins/src/nohup.rs:` module doc (:1-7), `execute` (:68-112), `rebuild_command_line` (:129-138); registration `factory.rs:331-338` `.transparent_background_wrapper()`.
**Signature:** `fn execute(&self, context) -> Future<Result<ExecutionResult>>` — runs operand via `context.shell.run_string(rebuilt_line)` with `params.process_group_policy = NewProcessGroup`.
**Data Shape:** `nohup <cmd>` foreground = run directly, surface exit status; `nohup <server> &` = brush unwraps the wrapper and spawns the OPERAND directly with session reparenting (double-fork out of the shell's descendant tree), so kill-on-drop teardown never reaches it. Missing operand → exit 125 like coreutils.

### Decisive source
```rust
// `nohup <cmd>` (foreground) runs the operand directly and surfaces its exit
// status. Persistence across the host's teardown is a *background* concern that
// never reaches this builtin: brush's `transparent_background_wrapper` unwraps
// `nohup <server> &` to spawn the operand directly with session reparenting,
// double-forking it out of the shell's descendant tree. Like coreutils, we run
// the operand here; we only differ by not masking SIGHUP.
```

**Flow:** parse (`--help`/`--version` only when SOLE argument — they used to be executed as commands exit 127; first `--` terminates options but mid-command `--` belongs to the operand) → empty command = 125 diagnostic → rebuild line with `quote_arg` per arg → run in new process group.
**Invariant:** A system nohup does NOT escape a process-group kill — that is exactly why this one shadows it. The wrapper flag is what moves the persistence semantics out of the builtin body into the shell's job spawner; ports without such a hook must implement session detachment themselves for the background case only.
**Probe:** direct tests pin parsing: `nohup.rs:151 leading_dashdash_ends_options`, :160 `dashdash_protects_operands_including_help` (`-- -- x` runs a command literally named `--`; `-- --help` runs one named `--help`), :167 `mid_command_dashdash_is_preserved`, :176 `leading_help_and_version_are_options`.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "transparent_background_wrapper nohup session reparenting", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps at pin (registration site factory.rs:331-338).

## Verdict
Adopt the shadow-the-system-binary rationale + wrapper-based detachment split. Adapt to your shell's background-spawn hook; if none exists, omit the foreground-only shortcut and detach explicitly. Keep the 125 missing-operand contract and sole-argument help rule byte-faithful.
