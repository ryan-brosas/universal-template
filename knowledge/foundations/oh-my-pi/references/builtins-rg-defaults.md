<!-- capsule-v2 -->
# rg stdin-vs-cwd default + display paths — how does an embedded ripgrep decide what to search?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** With no path operands, when does `rg PATTERN` search stdin versus the current directory, and how are result paths displayed?

## default_paths + display_path
**Path/Symbol:** `crates/pi-builtins/src/rg.rs:` `default_paths` (:1631-1640), call site :1901, `display_path` (:1255-1265), walk request :1240-1251, JSON stats printer (:1653-1677).
**Signature:** `fn default_paths(paths: &mut Vec<OsString>, use_implicit_stdin: bool)`; `fn display_path(operand: &OsStr, root: &Path, path: &Path) -> PathBuf`.
**Data Shape:** `use_implicit_stdin = !cli.files && !pattern_stdin_consumed && host.stdin_is_search_input()` — the Host flag set at build_host: fd0 is a PipeReader or in-process Stream (a shell pipe/capture), NOT a file/tty.

### Decisive source
```rust
if !paths.is_empty() { return; }
if use_implicit_stdin { paths.push(OsString::from("-")); } else { paths.push(OsString::from(".")); }
```
```rust
let rel = path.strip_prefix(root).unwrap_or(path);
if rel.as_os_str().is_empty() { return PathBuf::from(operand); }  // the root itself
if operand == OsStr::new(".") { rel.to_path_buf() }               // "./x" prints as "x"
else { Path::new(operand).join(rel) }                             // prefix preserved for other roots
```

**Flow:** no operands → stdin if fd0 looks like search input (and pattern didn't consume stdin via `-f -`), else implicit `.` recursive walk (WalkDetail::Minimal unless max-filesize needs metadata, PreOrder, one-file-system honored) → per-match path rendering strips the root prefix, collapses `.`, keeps explicit operand prefixes → optional JSON event stream with summary stats block.
**Invariant:** (1) The stdin decision is made from the SHELL's descriptor table, not process fd 0 — this is the embedded-shell analog of ripgrep's isatty heuristic and must consult the Host view. (2) Filename-prefix visibility ladder: --no-filename off; --with-filename/files-with-matches/vimgrep on; else recursive || >1 path. (3) Two prebuilt searchers exist per run (Automatic vs Explicit binary mode) so binary detection doesn't reconfigure mid-stream.
**Probe:** deterministic anchors: `grep -c 'fn default_paths' crates/pi-builtins/src/rg.rs` = 1; `grep -c 'stdin_is_search_input' crates/pi-builtins/src/rg.rs` = 1. Test modules rg.rs:1933 pin printer behavior (runner blocked this environment).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "rg default paths implicit stdin operand dot", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (`default_paths` rg.rs:1631).

## Verdict
Adopt the Host-view stdin heuristic + root-stripping display rules for any search tool inside an embedded shell. Adapt to your walker; keep the two-searcher binary-mode split and the `-`/`.` default pair.
