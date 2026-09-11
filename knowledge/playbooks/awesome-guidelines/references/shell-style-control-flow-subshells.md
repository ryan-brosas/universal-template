<!-- capsule-v2 -->
# Control flow and subshells — will state survive the pipeline?

**Source:** Google Shell Style Guide §Test/[[ ]], §Pipes to While, §Arithmetic. **Question:** Does this loop/pipeline mutate variables the caller needs?

## Test seam
**Path/Symbol:** `if [[ … ]]` / `(( … ))` conditionals.
**Signature:** `[[` for strings/patterns; `((` for integers; `==` not `=` for equality in `[[`.
**Data Shape:** quoted left-hand strings; unquoted RHS only when intentional regex in `=~`.

### Decisive contrast
```bash
# Preferred
if [[ "${name}" =~ ^[[:alnum:]]+ ]]; then … fi
if (( count > 3 )); then … fi

# Broken: [ uses word splitting / globbing
if [ "${name}" == f* ]; then … fi
```

**Flow:** pick `[[`/`((` → quote variables → avoid lexicographic `>` inside `[[` for numbers.
**Invariant:** `[`/`test` pathname-expand unquoted RHS; `[[` does not — prefer `[[` for string tests.
**Probe:** no bare `[` for new code; numeric compares use `(( ))` or `-gt`, not `[[ a > b ]]`.

## Subshell seam
```bash
# WRONG: last_line stays NULL in parent
your_command | while read -r line; do last_line="${line}"; done

# RIGHT
while read -r line; do last_line="${line}"; done < <(your_command)
# or: readarray -t lines < <(your_command)
```

**Flow:** need line iteration + parent state → process substitution or `readarray` → loop array in parent shell.
**Invariant:** pipe-to-while runs loop in subshell — assignments do not propagate upward.
**Probe:** no `| while read` when outer vars consumed after loop; no `for x in $(cmd)` for arbitrary line input.

## Verdict
Adopt `[[`/`((`/`readarray`; avoid pipe-subshell traps and `[` glob bugs. Learning note: `shell-style-learning-note.md`.
