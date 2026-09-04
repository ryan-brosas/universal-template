<!-- capsule-v2 -->
# Quoting for eval — heredoc/multiline special-casing and nul-redirect hygiene

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you single-quote an arbitrary command string for `eval '…'` without corrupting heredocs, multiline strings, or Windows-reserved filenames?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/shellQuoting.ts` — `containsHeredoc` with bit-shift exclusions (:7-22), `containsMultilineString` (:27-38), `quoteShellCommand` (:46-74), `hasStdinRedirect`/`shouldAddStdinRedirect` (:81-106), `rewriteWindowsNullRedirect` + `NUL_REDIRECT_REGEX` (:124-128).
**Signature:** `quoteShellCommand(command, addStdinRedirect=true) → string`.
**Data Shape:** heredoc/multiline ⇒ `'...'` with `'\"'\"'` escaping and NO stdin redirect; regular ⇒ shell-quote `quote([command, '<', '/dev/null'])`.

### Decisive source
```ts
// The model occasionally hallucinates Windows CMD syntax (e.g., `ls 2>nul`)
// even though our bash shell is always POSIX (Git Bash / WSL on Windows).
// When Git Bash sees `2>nul`, it creates a literal file named `nul` — a
// Windows reserved device name that is extremely hard to delete and breaks
// `git add .` and `git clone`. See anthropics/claude-code#4928.
```

**Flow:** heredoc-or-multiline commands bypass shell-quote (it over-escapes `!` to `\!` in those contexts) in favor of manual single-quote wrapping that escapes only embedded single quotes; heredocs additionally suppress the stdin redirect (the body provides input). Stdin redirect added only when absent (`<file` detection excludes `<<`, `<(`) — bit-shift arithmetic like `$((1<<2))` must not read as a heredoc. `>nul`/`2>nul`/`&>nul` rewritten case-insensitively to `/dev/null` before quoting, with word-boundary guard so `>null`/`nul.txt` survive; documented collateral: rewriting inside quoted strings accepted as harmless.

**Invariant:** (1) Escaping rules differ per content class: the `!`-over-escaping failure makes one universal quoter wrong — branch on content class FIRST. (2) Heredoc bodies are their own stdin: adding `< /dev/null` breaks termination. (3) Model-emitted Windows-isms need normalization at the quoting boundary, not per-tool fixes. (4) Regex rewrites without quote-awareness are acceptable only when misfires are provably harmless.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'reserved device name' src/utils/bash/shellQuoting.ts | head -1` → :114; `grep -nF 'aggressive escaping' src/utils/bash/shellQuoting.ts` → :54; graph resolves via bashProvider consumers; file has no direct Function nodes of its own beyond exports (BM25-invisible helpers — cite file:line).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "quoteShellCommand rewriteWindowsNullRedirect shouldAddStdinRedirect", limit: 5 });
```

## Verdict
Adopt the content-class branch plus the nul-normalization regex for any eval-quoting layer serving an LLM-produced command stream.
