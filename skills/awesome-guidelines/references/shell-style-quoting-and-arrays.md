<!-- capsule-v2 -->
# Quoting and arrays — how do arguments survive word splitting?

**Source:** Google Shell Style Guide §Quoting, §Arrays, §Command Substitution. **Question:** Will this expansion break on spaces, empty strings, or metacharacters?

## Quoting seam
**Path/Symbol:** any `"${var}"` expansion site.
**Signature:** double-quote variables; single-quote literals; `$(command)` not backticks.
**Data Shape:** strings, lists as arrays — never space-joined flag strings.

### Decisive patterns
```bash
declare -a FLAGS=( --foo --bar='baz' )
mybinary "${FLAGS[@]}"

for arg in "$@"; do
  echo "argument: ${arg}"
done

flag="$(some_command "$@" 'literal')"
```

**Flow:** build list → store in array → expand with `"${arr[@]}"` → pass to command without `eval`.
**Invariant:** `"$@"` preserves argument boundaries; unquoted `$@`/`$*` splits and drops empties; brace `"${var}"` required for safe expansion (braces alone are not quoting).
**Probe:** ShellCheck SC2086/SC2048 absent; no backticks; no `flags='--a --b'; mybinary ${flags}` anti-pattern.

## Empty and optional args
**Flow:** test emptiness with `[[ -z "${var}" ]]` → optional flags via `${var:+"--flag" "${var}"}`.
**Invariant:** never use filler suffix tests (`"${var}X"`) or bare `[[ "${var}" ]]` when `-n`/`-z` clarifies intent.
**Probe:** review shows `-z`/`-n` for optional strings; command substitutions quoted even when expecting integers.

## Verdict
Adopt `"${var}"`, arrays for lists, `"$@"` for forwarding; omit string-built flag lines and backticks. Learning note: `shell-style-learning-note.md`.
