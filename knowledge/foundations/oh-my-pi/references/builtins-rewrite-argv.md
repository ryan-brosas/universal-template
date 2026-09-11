<!-- capsule-v2 -->
# rewrite_argv pre-parse ladder — how do utilities accept syntax clap cannot model?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85`; Codebase Memory `oh-my-pi`. **Question:** Before clap sees argv, which GNU/BSD obsolete spellings must be rewritten, and where do the 15 hooks live?

## The Utility::rewrite_argv seam
**Path/Symbol:** `crates/pi-builtins/src/host.rs:71-73` (default identity); implementations in `cut.rs:28` (`-d=` → `--delimiter==`), `head.rs:1368` (`arg_iterate` obsolete `-NUM`), `yes.rs:29`, `uniq.rs:760` (obsolete `+N`/`-N` skip counts → `--skip-fields/--skip-chars` when modern flag absent), `date.rs:1313`, `diff.rs:156`, `grep.rs:1437`, `ls.rs:3760`, `mktemp.rs:282`, `rm.rs:667`, `sed.rs:9360`, `seq.rs:534`, `stat.rs:1921` (`rewrite_bsd_invocation`), `tail.rs:2989`.
**Signature:** `fn rewrite_argv(argv: Vec<OsString>) -> Result<Vec<OsString>, String>` — `Err(message)` renders `<NAME>: <message>` on stderr and exits `USAGE_ERROR`.
**Data Shape:** argv[0] is the command name; rewriters may insert/remove tokens but must keep operand bytes verbatim (`OsString`, not lossy strings).

### Decisive source
```rust
// yes.rs — GNU yes recognizes --help/--version ONLY as the sole argument;
// everything else is echoed verbatim. Insert `--` so clap treats every
// remaining argument as an operand.
if argv.is_empty()
	|| (argv.len() == 2 && matches!(argv[1].to_str(), Some("--help" | "--version")))
{ return Ok(argv); }
if argv.get(1).is_some_and(|arg| arg.to_str() == Some("--")) { argv.remove(1); } // GNU consumes one leading --
argv.insert(1, OsString::from("--"));
```
```rust
// head.rs:178 — lowercase suffixes are byte multipliers (obsolete BSD `-Nc/-Nb/-Nk/-Nm`);
// uppercase suffixes mirror the modern `-n NUM<suffix>` form and scale LINES
// (`head -10K` == `head -n 10240`).
```

**Flow:** adapter materializes process-substitution fds first, then calls `rewrite_argv`, then clap parses; a rewrite failure is reported on the utility's own terms (not brush's generic usage-error path).
**Invariant:** The hook exists because clap treats unknown short clusters as errors — e.g. `head -5` must become `head -n 5`. Rewrites preserve ORDER of q/v/z flags and never mutate operands after `--`. Case-sensitivity of suffixes is semantic (bytes vs lines), not cosmetic.
**Probe:** deterministic anchors: `grep -c 'fn parse_obsolete' crates/pi-builtins/src/head.rs` = 1; test pins at `head.rs:257` `obsolete` helper + `cut.rs:28` comment "GNU cut accepts `-d=` as a delimiter spelling".
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "rewrite_argv obsolete head minus count", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85: rank-1 `Head.rewrite_argv head.rs:1368-1370`.

## Verdict
Adopt a pre-clap argv rewrite seam for any CLI-faithful builtin port; enumerate your host's unmodelable syntaxes per utility instead of weakening the argument model. Adapt the specific rewrites to the utilities you port; omit MSYS-specific handling.
