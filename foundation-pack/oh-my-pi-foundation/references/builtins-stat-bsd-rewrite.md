<!-- capsule-v2 -->
# stat BSD-invocation detection — rewriting `stat -f "%Sm %N"` into GNU argv pre-clap

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT `main@4854db85` (uutils port); Codebase Memory `oh-my-pi`. **Question:** How can one binary accept both BSD and GNU stat dialects when `-f` means opposite things?

## rewrite_bsd_invocation
**Path/Symbol:** `crates/pi-builtins/src/stat.rs:` doc + fn (:1425-1488), `BsdStyle` (:1490-1498), `bsd_to_gnu_argv` (:1501+), printf newline rule :1039, escape-survival note :1604.
**Signature:** `fn rewrite_bsd_invocation(argv: &[OsString]) -> Option<Result<Vec<OsString>, String>>` — None = not BSD-shaped; Some(Err) = BSD-shaped but unsupported directive.
**Data Shape:** Detection heuristics: a `-f` cluster whose attached/next value contains `%`, or any cluster of BSD booleans (`L n q F s x`) containing `-s` (shell output) or `-x` (verbose) — GNU filesystem mode would have to target a file literally named like a format string, "which never happens in practice".

### Decisive source
```rust
// Detected invocations are rewritten to the GNU equivalent (`-c`/`--printf`
// plus a translated format, or hidden style/timefmt options) BEFORE clap parsing.
if format.is_some_and(|f| f.contains('%')) { detected = true; break; }
...
'q' | 'F' => {},   // -q suppress-errors and -F ls-type decorations: no GNU counterpart worth emulating
's' => style = Some(BsdStyle::Shell),    // eval-able st_dev=… assignments; LAST style wins
'x' => style = Some(BsdStyle::Verbose),  // Linux-like verbose block
```

**Flow:** scan tokens until `--` → detect → re-parse the cluster grammar by hand (attached vs next-token values for f/t) → emit GNU argv (`-c` or `--printf` per trailing-newline flag, hidden style/timefmt options) → clap parses the rewritten argv normally. `--printf` additionally suppresses the mandatory trailing newline and its escape processing must survive `%b`-style escapes unchanged.
**Invariant:** Rewriting happens BEFORE clap so help/errors stay in one dialect. Operands keep original possibly-non-UTF8 bytes through the rewrite. Last-style-wins mirrors BSD. A wrong guess here silently changes meaning of `-f` (filesystem mode), hence the %-heuristic plus boolean-cluster corroboration rather than naive prefix match.
**Probe:** deterministic anchors: `grep -c 'fn rewrite_bsd_invocation' crates/pi-builtins/src/stat.rs` = 1; direct tests exist in stat.rs test module (:3010 `empty_file_reports_regular_empty_file` pins output shapes).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "rewrite_bsd_invocation stat format percent", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved @4854db85 via anchor greps (stat.rs:1441).

## Verdict
Adopt the detect-then-rewrite pattern for dual-dialect CLIs: keep clap parsing single-dialect by translating the foreign dialect up front. Adapt directive translation tables; preserve the never-happens-in-practice rationale comments — they justify the heuristic to future maintainers.
