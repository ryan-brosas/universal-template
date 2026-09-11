---
title: shell-scripting-practices
summary: Use when authoring or reviewing bash glue scripts, scope limits, quoting and arrays, subshell-safe loops, main/local structure, STDERR errors, and ShellCheck; distilled from Google Shell Style Guide.
kind: playbook
---

# Shell Scripting Practices

Application skill for shell.

## Core Principle

Bash is for **thin orchestration**, quote aggressively, avoid subshell traps, check every mutation, and migrate before scripts become undebuggable programs.

## When to Use / NOT

- Writing or reviewing `.sh` utilities, CI glue, or agent shell runners.
- Debugging word-splitting, empty-arg, or pipe-subshell bugs.

**NOT when:**

- Logic exceeds ~100 lines or needs structured data, use Python/Go/etc.
- PowerShell-only environment, use `powershell-scripting-practices`.

## Workflow

1. **Scope**, confirm shell is appropriate; bash shebang + `set` for strict modes if project uses them.
2. **Arguments**, `"$@"` forwarding; arrays for flag lists; quote all expansions.
3. **Conditionals**, `[[`/`((`/`readarray`; no pipe-to-while when parent needs state.
4. **Structure**, constants → functions → `main "$@"`; `local` + split declare/assign; STDERR `err()`.
5. **Verify**, `shellcheck` exit 0; exercise empty args, spaces in paths, and failure paths; read a piped command's status from `set -o pipefail` or `${PIPESTATUS[0]}`, because `$?` after a pipe is the last stage's status.

## Red Flags

- Unquoted `$var` or `$@`.
- `eval`, SUID bit, or string-built command lines.
- `cmd | while read` then read parent variable.
- `local x="$(cmd)"` followed by `$?` check.
- `cmd | tail` (or `| grep`) followed by a `$?` check, or under `set -e`: without `pipefail` a failing command passes green.
- Script past 100 lines without migration plan.

## Verification

- `shellcheck -x script.sh` (or project wrapper) exit 0.
- Manual: args with spaces, empty optional flags, failing command path, and a failing command inside a pipeline still exits nonzero.
