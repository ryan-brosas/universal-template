<!-- capsule-v2 -->
# pgrep/pkill/pidwait shared engine — one selector grammar, three front ends, mode-gated flags

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** How do three commands share selection/parse/help while differing only in what they DO with selected processes?

## ProcMatchMode run()
**Path/Symbol:** `crates/pi-builtins/src/proc_match.rs:` `enum ProcMatchMode` (:32-36), `pub(crate) fn run(mode, argv, context)` (:79-267), `parse_proc_match_args` (:319-610), `select_processes` (:631-752), `pidfile_is_locked` (:899-913).
**Signature:** `fn select_processes(options) -> Result<(Vec<ProcInfo>, HostProcesses), String>` — ONE `ProcInfo::all()` snapshot serves both selection and the host chain.
**Data Shape:** `ProcMatchOptions` ~25 fields; patterns joined `(?:p1)|(?:p2)` (exact wraps each as `^(?:p)$`); `-F -` reads pids from stdin; `-L/--logpidfile` requires the pidfile to hold a flock.

### Decisive source
```rust
// macOS pgrep semantics differ: -a means include ancestors in SELECTION (not list-full),
// ancestors are EXCLUDED from matching by default unless -a given or -v set.
let exclude_ancestors = options.ignore_ancestors
	|| (cfg!(target_os = "macos") && !options.include_ancestors && !options.invert);
...
let matches = pattern_matches && selectors_match;
if matches != options.invert { selected.push(process); }
selected.sort_by_key(|process| (process.start_time(), process.pid()));
if options.newest  { selected = selected.into_iter().next_back().into_iter().collect(); } // -n
else if options.oldest { selected.truncate(1); }                                          // -o
```

**Flow:** hand-rolled parser (clap can't express pgrep's flag soup): leading `-SIGNAL` only in Kill mode index-0 → long opts with `=` or next-token values → short clusters with attached values → pidfile expansion (flock check via F_GETLK when `-L`) → validation ladder (`-F`+`-p` exclusive, `-L` requires `-F`, one pattern off-macOS, `-v` XOR `-n/-o`) → select (group/session value 0 = HOST's own, substituted before compare) → mode dispatch: Grep prints pid[/name/full] joined by delimiter; Kill loops with per-pid cancel checks + optional `-I` confirmation (AsyncFd-guarded stdin read) + ancestor refusal + per-process echo variants; Wait polls `status()==Exited` every 50 ms under tokio::select on cancel token.
**Invariant:** (1) Exit codes follow procps: no match = 1, usage/syntax = 2, pidfile errors = 3. (2) Selection may legitimately INCLUDE an ancestor — signalling one is refused late at delivery (`host.pids.contains` → stderr note + continue), never at selection. (3) `-q` is THREE different flags by mode (quiet grep / queue-value kill-linux / error otherwise) — mode gates every ambiguous spelling.
**Probe:** `proc_match.rs:964` windows-only msys pidfile test is platform-gated; deterministic anchors: `grep -c 'refusing to signal pid' crates/pi-builtins/src/proc_match.rs` = 1; `grep -c 'fn pidfile_is_locked' crates/pi-builtins/src/proc_match.rs` = 2 (unix + stub).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "select_processes newest oldest invert sort start_time", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: `pidfile_is_locked#cfg(unix)] proc_match.rs:899-913` rank-1 for pidfile query.

## Verdict
Adopt the mode-dispatch engine + exit-code taxonomy + late ancestor refusal for any pgrep-family port. Adapt the parser to your arg framework but keep the mode-gated flag semantics table; omit Linux-only `--queue`/sigqueue unless you need queued signals.
