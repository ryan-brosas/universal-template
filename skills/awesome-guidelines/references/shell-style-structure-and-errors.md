<!-- capsule-v2 -->
# Structure and errors — can a reader find main and trust exit codes?

**Source:** Google Shell Style Guide §main, §Local Variables, §Checking Return Values, §STDOUT vs STDERR. **Question:** Does the script fail loudly, check mutations, and expose a clear entrypoint?

## Structure seam
**Path/Symbol:** multi-function script bottom: `main "$@"`.
**Signature:** constants readonly at top → functions block → `main` last.
**Data Shape:** `local` vars inside functions; separate `local x` / `x="$(cmd)"` when checking `$?`.

### Decisive local/$? trap
```bash
my_func() {
  local result
  result="$( fragile_cmd )"
  (( $? == 0 )) || return
}
# NOT: local result="$(fragile_cmd)"  # $? is from local, always 0
```

**Flow:** declare locals → run command → capture `$?` before next command → return/exit with message on failure.
**Invariant:** function-specific state must use `local`; `local var="$(cmd)"` hides command exit status.
**Probe:** multi-function files end with `main "$@"`; functions grouped near top; no executable code between function definitions.

## Error seam
```bash
err() { echo "[$(date +'%Y-%m-%dT%H:%M:%S%z')]: $*" >&2; }

if ! mv "${files[@]}" "${dest}/"; then
  err "Unable to move ${files[*]} to ${dest}"
  exit 1
fi
```

**Flow:** status to STDOUT; problems to STDERR via `err` → check every mutating command → pipeline failures via immediate `PIPESTATUS` copy.
**Invariant:** unchecked `mv`/`rm`/`curl` in scripts that claim to be production glue is a review reject.
**Probe:** ShellCheck SC2181 addressed; errors go to `>&2`; `shellcheck script.sh` exit 0 (or documented disables with reason).

## Verdict
Adopt `main`, `local`, explicit return checks, STDERR errors, ShellCheck gate. Learning note: `shell-style-learning-note.md`.
