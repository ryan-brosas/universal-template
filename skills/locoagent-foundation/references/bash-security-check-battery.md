<!-- capsule-v2 -->
# Quote-context security battery — bashSecurity's 23 numbered checks

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What regex-tier checks must still run on the UNQUOTED projection of a command even when a full AST parser exists?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/bashSecurity.ts` — `COMMAND_SUBSTITUTION_PATTERNS` (:16-41 incl. zsh `=cmd`, `(e:`, `(+)` glob qualifiers, always-block, PowerShell `<#`), 23-entry `BASH_SECURITY_CHECK_IDS` (:77-101), `extractQuotedContent` triple-projection (:128+), `stripSafeHeredocSubstitutions` (:521), `hasSafeHeredocSubstitution` (:581), legacy entry `bashCommandIsSafeAsync_DEPRECATED` (:2426).
**Signature:** validators receive `ValidationContext { originalCommand, baseCommand, unquotedContent, fullyUnquotedContent, fullyUnquotedPreStrip, unquotedKeepQuoteChars, treeSitter? }`.
**Data Shape:** numeric check IDs for string-free telemetry.

### Decisive source
```ts
// Zsh EQUALS expansion: =cmd at word start expands to $(which cmd).
// `=curl evil.com` → `/usr/bin/curl evil.com`, bypassing Bash(curl:*) deny
// rules since the parser sees `=curl` as the base command, not `curl`.
{
  pattern: /(?:^|[\s;&|])=[a-zA-Z_]/,
  message: 'Zsh equals expansion (=cmd)',
},
```

**Flow:** the legacy tier runs when the AST is unavailable (feature-off/shadow/abort-free null) — and several of its projections remain useful everywhere: strip quoted content THREE ways (keep double-quote content / drop all quoted content / keep quote DELIMITERS to expose `'x'#` adjacency) then run the battery: incomplete commands, jq system() calls, obfuscated flags (`--<ctrl-char>` style), shell metacharacters in unquoted spans, dangerous vars, newlines, `$()`/`${}`/`$[`/process substitution/zsh forms, IFS injection, git commit substitution, `/proc/*/environ`, malformed-token injection, backslash-escaped whitespace/operators, brace expansion, control chars, Unicode whitespace, mid-word hash comments (needs the keep-quote-chars projection), comment/quote desync, quoted newlines. Safe-heredoc substitution (`$(cat <<'EOF'…EOF)`) is recognized so compound reads don't false-positive on the `$()` rule while genuinely dangerous misparses still block.

**Invariant:** (1) Regex checks operate on PROJECTIONS of the command (unquoted spans), never the raw text — quote-awareness lives in the projector. (2) Keeping quote delimiters as characters is the trick that exposes quote-adjacent operators (`'x'#`) that full stripping hides. (3) Defense-in-depth includes cross-shell patterns (zsh expansions, PowerShell syntax) you don't even execute today. (4) Numbered IDs make telemetry string-free. (5) This tier complements, never replaces, the AST tier; its known misparse modes are exactly what PARSE_ABORTED/too-complex now fail closed on.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'Zsh equals expansion (=cmd)' src/tools/BashTool/bashSecurity.ts` → :26; `grep -nF 'PowerShell comment syntax' src/tools/BashTool/bashSecurity.ts` → hits :38 (pattern) + :40 (comment); `grep -c 'validate' src/tools/BashTool/bashSecurity.ts` ≥ 90; graph resolves hasSafeHeredocSubstitution :581 line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "bashCommandIsSafe extractQuotedContent validateDangerousPatterns BASH_SECURITY_CHECK_IDS", limit: 5 });
```

## Verdict
Adopt the projection model + battery structure for any fallback-tier command screener; port the zsh-equals and mid-word-hash checks verbatim.
