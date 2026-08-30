<!-- capsule-v2 -->
# Shell scope — when is bash the right tool?

**Source:** Google Shell Style Guide §Background, §SUID, §Wildcard Expansion. **Question:** Should this logic stay in shell or move to another language?

## Scope seam
**Path/Symbol:** executable `*.sh` / PATH utility.
**Signature:** `#!/bin/bash` + `set` options at top.
**Data Shape:** linear glue calling external commands; no rich in-memory structures.

### Decisive limits
```bash
#!/bin/bash
# OK: orchestrate tar + ssh with flags
# NOT OK: 200-line state machine with nested JSON parsing — rewrite in Python/Go
```

**Flow:** assess task → mostly CLI delegation with little data work → stay shell → if lines/complexity grow past threshold → migrate before rewrite cost compounds.
**Invariant:** bash is the **only** permitted shell for executables here; no SUID/SGID on scripts — use `sudo` for elevation.
**Probe:** script ≤100 lines OR explicit exception documented; `file` shows bash shebang; no setuid bit; ShellCheck clean on scope-related warnings.

## Wildcard safety
**Flow:** user-supplied or directory glob → prefix `./` before `*` expansion → pass quoted paths to commands.
**Invariant:** bare `*` can expand to `-`-leading names and become flags (`rm *` deletes `-f` as file, not flag — still dangerous for other tools).
**Probe:** grep shows `\./\*` or loop over array from `readarray`, not unquoted `*`.

## Verdict
Adopt bash for thin glue only; migrate early when complexity grows; forbid SUID; use `./` for globs. Learning note: `shell-style-learning-note.md`.
