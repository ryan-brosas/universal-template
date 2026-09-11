<!-- capsule-v2 -->
# Legacy splitCommand — continuation parity, salted placeholders, static redirect targets

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** When you must split a compound shell command with a regex/tokenizer hybrid, which line-joining and placeholder rules keep the split consistent with what bash executes?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/commands.ts` — salted `generatePlaceholders` (:19-40), `isStaticRedirectTarget` (:49-83), `splitCommandWithOperators` (:85-249), comment-token ReDoS guard (:202-215 region), `splitCommand_DEPRECATED` (:265), `extractOutputRedirections` (:634).
**Signature:** `splitCommandWithOperators(cmd) → (string | operator)[]`; `splitCommand_DEPRECATED(cmd) → string[]`.
**Data Shape:** tokens with injected quote/newline placeholders; operators preserved as separate elements.

### Decisive source
```ts
// SECURITY: We must only join when there's an ODD number of backslashes before the newline.
// With an even number (e.g., `\\<newline>`), the backslashes pair up as escape sequences,
// and the newline is a command separator, not a continuation. Joining would cause us to
// miss checking subsequent commands (e.g., `echo \\<newline>rm -rf /` would be parsed as
// one command but shell executes two).
```

**Flow:** extract heredocs first (see heredoc capsule) → join backslash-newline continuations ONLY on odd backslash counts, computing the SAME join independently for the original command so parse-failure fallback returns the joined form (exploit documented: pre-join `$`+`{}` split across lines hides `${}` patterns while bash joins them) → inject random-salted placeholders for quotes/newlines/escapes that the tokenizer strips → collapse adjacent strings + globs → strip injected-quote prefixes from comment tokens to stop exponential double-quoting across recursive splits (ReDoS via catastrophic chunker backtracking) → restore placeholders. Redirect targets count as static ONLY if a single shell word: reject whitespace/quotes (`cat > out /etc/passwd` merges into target "out /etc/passwd" hiding the read path), empty string (path.resolve('') = cwd = always-allowed), and word-initial `#` differentials.

**Invariant:** (1) Continuation joining must mirror bash's escape pairing exactly — parity errors silently merge or split command boundaries between checker and executor. (2) The fallback representation after ANY parse failure is the JOINED original as ONE subcommand, never the raw text. (3) Placeholders are per-parse random: literal-collision injection dies here. (4) A redirect target containing whitespace/quotes is NOT a path — treating merged blobs as targets hides the real operands from validation. (5) Recursive re-splits of restored text must not re-inject quotes unboundedly (strip-before-unplaceholder).

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'ODD number of backslashes' src/utils/bash/commands.ts` → :101; `grep -nF 'catastrophically backtrack' src/utils/bash/commands.ts` → :208; `grep -nF 'always allowed' src/utils/bash/commands.ts` → :57; graph `search_graph --project locoagent --query splitCommandWithOperators extractOutputRedirections` → :85-249 / :634 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "splitCommandWithOperators generatePlaceholders isStaticRedirectTarget extractOutputRedirections", limit: 5 });
```

## Verdict
Adopt for legacy/regex-tier splitting; every rule here exists because a bypass was demonstrated — port with the comments attached.
