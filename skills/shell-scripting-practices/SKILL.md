---
name: shell-scripting-practices
description: "Use when authoring or reviewing bash glue scripts, scope limits, quoting and arrays, subshell-safe loops, main/local structure, STDERR errors, and ShellCheck; distilled from Google Shell Style Guide."
invocation: manual
disable-model-invocation: true
---

# Shell Scripting Practices

Application skill for shell learning (from the archived `awesome-guidelines` style capsules). Load learning note for *why*; capsules for probes.

## Core Principle

Bash is for **thin orchestration**, quote aggressively, avoid subshell traps, check every mutation, and migrate before scripts become undebuggable programs.

## When to Use / NOT

- Writing or reviewing `.sh` utilities, CI glue, or agent shell runners.
- Debugging word-splitting, empty-arg, or pipe-subshell bugs.

**NOT when:**

- Logic exceeds ~100 lines or needs structured data, use Python/Go/etc.
- PowerShell-only environment (see awesome-guidelines PowerShell guide separately).

## Workflow

1. **Scope**, confirm shell is appropriate; bash shebang + `set` for strict modes if project uses them (`shell-style-scope-and-safety.md`).
2. **Arguments**, `"$@"` forwarding; arrays for flag lists; quote all expansions (`shell-style-quoting-and-arrays.md`).
3. **Conditionals**, `[[`/`((`/`readarray`; no pipe-to-while when parent needs state (`shell-style-control-flow-subshells.md`).
4. **Structure**, constants → functions → `main "$@"`; `local` + split declare/assign; STDERR `err()` (`shell-style-structure-and-errors.md`).
5. **Verify**, `shellcheck` exit 0; exercise empty args, spaces in paths, and failure paths.

## Red Flags

- Unquoted `$var` or `$@`.
- `eval`, SUID bit, or string-built command lines.
- `cmd | while read` then read parent variable.
- `local x="$(cmd)"` followed by `$?` check.
- Script past 100 lines without migration plan.

## Verification

- `shellcheck -x script.sh` (or project wrapper) exit 0.
- Manual: args with spaces, empty optional flags, failing command path.
- Capsule checklist on review.


## References

- `awesome-guidelines/references/shell-style-learning-note.md`
- `awesome-guidelines/references/shell-style-scope-and-safety.md`
- `awesome-guidelines/references/shell-style-quoting-and-arrays.md`
- `awesome-guidelines/references/shell-style-control-flow-subshells.md`
- `awesome-guidelines/references/shell-style-structure-and-errors.md`
