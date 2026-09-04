<!-- capsule-v2 -->
# Shell-arg validation — what is the minimal deny-list that makes a path safe to splice into a shell command?

**Source:** codebase-memory-mcp MIT `main@010569fa6ce1bc5d6430f858129243ea1a2e3fd5`; Codebase Memory `ext-codebase-memory-mcp`. **Question:** Which characters must be rejected before interpolating user-controlled paths into `sh -c`-style commands?

## Deny-by-metachar with per-platform backslash policy
**Path/Symbol:** `src/foundation/str_util.c:cbm_validate_shell_arg` (246–272) + `cbm_validate_shell_path_arg` (274+).
**Signature:** `bool cbm_validate_shell_arg(const char *s);`
**Data Shape:** Rejects `'`, `"`, `;`, `|`, `&`, `$`, backtick, `<`, `>`, `\n`, `\r` always, plus `\` on POSIX (safe separator on Windows cmd contexts). Callers wrap the validated value in DOUBLE quotes — safe only because the active metacharacters inside double quotes are already rejected.

### Decisive source
```c
/* git -C "<path>" works on both cmd.exe and POSIX shells. Double quotes are
 * safe here because cbm_validate_shell_arg (above) rejects ", $, `, \ and the
 * other shell metacharacters that would otherwise be active inside them. */
```

**Flow:** validate → reject on ANY listed char (no escaping attempt — fail closed) → caller embeds inside hard-coded double quotes in a fixed command template (`git -C "%s" log ...`) → popen runs it.
**Invariant:** Validation and quoting are a PAIR: rejecting `$`/backtick/quote is exactly what makes double-quoting sufficient; loosening either side breaks the other. Path variant additionally requires an existing-path shape.
**Probe:** `tests/test_security.c:shell_rejects_*` matrix (single quote, dollar subst, backtick, semicolon, pipe, ampersand, newline, CR, NUL, redirect in/out, quote-escape attack, command substitution, env expansion) and `shell_accepts_clean_path/spaces/dots_dashes`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-codebase-memory-mcp", query: "cbm_validate_shell_arg", limit: 5 });
```

## Verdict
Adopt deny-list + fixed-double-quote-template as one indivisible contract; adapt the platform-specific backslash rule to your shells; prefer exec-without-shell entirely where possible — this is the fallback.
