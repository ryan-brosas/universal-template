<!-- capsule-v2 -->
# process-substitution fd materialization — why /dev/fd/<n> must be rewritten before exec

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How does `diff <(a) <(b)` work when the shell's descriptor table is not the process's?

## materialize_process_substitution_fds
**Path/Symbol:** `crates/pi-builtins/src/host.rs:` `process_substitution_fd` (:908-915), `materialize_process_substitution_fds` (:924-943), call site :740, ownership comment :771-773.
**Signature:** `fn materialize_process_substitution_fds(context, argv: &mut [OsString]) -> Result<Vec<OwnedFd>, Error>` — unix-only.
**Data Shape:** Recognizes `/dev/fd/<shell-fd>` args; for each resolvable ShellFd, dups the OpenFile to a real OwnedFd of the HOST PROCESS and rewrites the arg in place; returned Vec<OwnedFd> keeps dup'd fds alive through spawn_blocking.

### Decisive source
```rust
/// Brush allocates process-substitution pipes in its own descriptor table, so
/// the shell fd number in the argument is meaningless to `open`.
let fd = file.try_borrow_as_fd()?.try_clone_to_owned()?;
*arg = OsString::from(format!("/dev/fd/{}", fd.as_raw_fd()));
fds.push(fd);
```

**Flow:** BEFORE rewrite_argv/clap (raw OsStrings still intact) → scan argv → dup+rewrite → the Vec is MOVED INTO the blocking task closure (`let _process_substitution_fds = ...`) so drop happens only after the utility exits.
**Invariant:** (1) Materialization must precede parsing: utilities see ordinary `/dev/fd/N` paths and need no awareness. (2) Lifetime = the whole utility run; dropping early hands out open-then-EOF garbage. (3) Unresolvable shell fds are silently left as-is (the utility will fail opening them — matching shell behavior where the substitution already failed). (4) Windows omits the feature entirely (cfg-gated).
**Probe:** deterministic anchors: `grep -c 'meaningless to' crates/pi-builtins/src/host.rs` = 1; `grep -c 'fn materialize_process_substitution_fds' crates/pi-builtins/src/host.rs` = 1. Consumer coverage: diff tests exercise `<( )` operands via the same path.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "process substitution dev fd materialize ownedfd", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (host.rs:924).

## Verdict
Adopt pre-parse fd translation with task-lifetime ownership for any embedded runtime exposing bash-style process substitution. Adapt to your descriptor table API; keep silent passthrough for unresolvable fds.
