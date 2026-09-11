# Shell scripting — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `shell-style-*.md` capsules, `shell-scripting-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [Google Shell Style Guide](https://google.github.io/styleguide/shellguide.html) | Bash-only executables; scope limits (≤100 lines / simple glue); quoting/`[[ ]]`/arrays/`"$@"`; subshell pipe traps; `main` structure; return-value checks; STDERR for errors; ShellCheck; no SUID/eval |
| [ShellCheck](https://github.com/koalaman/shellcheck) (tool listed on awesome-guidelines) | Static analysis for common bash bugs — Google recommends for all scripts; complements style guide probes |

## Mental model

Shell is a **glue language**, not a development platform. Google permits bash for small utilities that orchestrate other programs with minimal data manipulation. Complexity budget is low: past ~100 lines or non-trivial control flow, rewrite in a structured language before the script accretes unmaintainable state.

Within that budget, correctness comes from **quoting discipline** and **awareness of bash parsing traps**: word splitting, pathname expansion, subshells in pipelines, and `$?` races with `local var="$(cmd)"`. The style guide is essentially a defense-in-depth checklist against footguns that ShellCheck also flags.

Security posture: **no SUID/SGID** on shell scripts (use `sudo`); avoid `eval`; expand globs with `./` prefix so leading `-` filenames cannot hijack flags.

## Decision tables

### When shell is acceptable

| Situation | Verdict |
|---|---|
| Thin wrapper calling other CLIs, little data shaping | OK |
| Performance-sensitive logic | Use another language |
| >100 lines or complex control flow | Rewrite now |
| Needs rich data structures | Not shell |

### Interpreter & file shape

| Element | Rule |
|---|---|
| Shebang | `#!/bin/bash`; set options via `set` so `bash script.sh` works |
| Executables | `.sh` or no extension (PATH binaries prefer no ext) |
| Libraries | `.sh`, not executable |
| SUID/SGID | Forbidden |

### Quoting & arguments

| Pattern | Rule |
|---|---|
| Variables in strings | `"${var}"` (brace + double-quote) |
| Positional args | `"$@"` almost always; `"$*"` only when joining intentionally |
| Command substitution | `$(cmd)` not backticks |
| Lists / flags | `declare -a`; expand with `"${arr[@]}"` |
| Empty tests | `[[ -z "${v}" ]]` / `[[ -n "${v}" ]]` not filler chars |
| Comparisons | `[[ … ]]` not `[`/`test`; numeric: `(( … ))` or `-gt` |

### Control flow & subshells

| Pattern | Problem | Fix |
|---|---|---|
| `cmd \| while read` | while runs in subshell; vars lost | `while read … done < <(cmd)` or `readarray` |
| `for x in $(cmd)` | splits on whitespace, not lines | `readarray` + loop |
| `rm *` | `-`-prefixed filenames become flags | `rm ./*` or explicit paths |
| `(( i++ ))` with `set -e` | zero exit can abort | know arithmetic exit semantics |

### Structure & errors

| Element | Rule |
|---|---|
| Errors | to STDERR; helper like `err()` |
| Functions | lower_snake; `local` in functions; declare/assign split when using `$?` |
| Layout | constants → functions → `main "$@"` at bottom for multi-function scripts |
| Return codes | check `$?` / `if ! cmd`; pipelines use `PIPESTATUS` immediately |
| Tooling | run ShellCheck on every script |

## Anti-patterns

- Unquoted `$var` / `$@` in data paths.
- String-accumulated flags then `eval` or unquoted expansion.
- Piping into `while` then expecting parent-scope updates.
- `[`/`test` with unquoted globs on RHS.
- SUID shell scripts.
- Aliases inside scripts (use functions).
- Skipping return-value checks on mutating commands.

## Skill trace

| Artifact | Role |
|---|---|
| `shell-style-scope-and-safety.md` | when bash, size limit, SUID, globs |
| `shell-style-quoting-and-arrays.md` | quotes, arrays, `$@`, substitution |
| `shell-style-control-flow-subshells.md` | `[[ ]]`, pipes, readarray |
| `shell-style-structure-and-errors.md` | main/local, STDERR, exit codes, ShellCheck |
| `shell-scripting-practices` | application skill for authoring/review |
