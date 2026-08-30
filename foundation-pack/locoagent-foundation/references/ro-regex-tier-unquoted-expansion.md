<!-- capsule-v2 -->
# Regex-tier fallback & unquoted-expansion guard — the hand-written regex layer beneath the flag walker, and the quote tracker that keeps it honest

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** For simple commands that don't merit a flag table, how do you keep regex allowlists from being bypassed by globs, `$VAR` expansion, or anchored-version suffix tricks?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/readOnlyValidation.ts` — `makeRegexForSafeCommand` (:1422-1425), `READONLY_COMMANDS` name list (:1432-1503), `READONLY_COMMAND_REGEXES` set incl. echo/uniq/jq/find/cd/ls regexes and anchored `node -v` family (:1509-1570), `containsUnquotedExpansion` (:1600-1669), `isCommandReadOnly` composition (:1678-1752) with git `-c`/`--exec-path`/`--config-env` post-filters (:1721-1747).
**Signature:** `function containsUnquotedExpansion(command: string): boolean`; `makeRegexForSafeCommand(command: string): RegExp` → `/^command(?:\s|$)[^<>()$`|{}&;\n\r]*$/`.
**Data Shape:** char-scan state machine: `inSingleQuote`, `inDoubleQuote`, `escaped`.

### Decisive source
```ts
// SECURITY: Only treat backslash as escape OUTSIDE single quotes. In bash,
// `\` inside `'...'` is LITERAL — it does not escape the next character.
// Without this guard, `'\'` desyncs the quote tracker: the `\` sets
// escaped=true, then the closing `'` is consumed by the escaped-skip
// instead of toggling inSingleQuote. ...
// Example: `ls '\' *` — bash sees glob `*`, but desynced parser thinks
// `*` is inside quotes → returns false (glob NOT detected).
if (currentChar === '\\' && !inSingleQuote) {
  escaped = true
  continue
}
```
And the expansion vector:
```ts
// Variables: `uniq --skip-chars=0$_` — bash expands `$_` at runtime to the
// last arg of the previous command. With IFS word splitting, this smuggles
// positional args past "flags-only" regexes like uniq's `\S+`. The `$` token
// check inside isCommandSafeViaFlagParsing only covers COMMAND_ALLOWLIST
// commands; hand-written regexes in READONLY_COMMAND_REGEXES (uniq, jq, cd)
// have no such guard.
```

**Flow:** `isCommandReadOnly`: trim trailing `2>&1` → UNC check → unquoted-glob/expandable-`$` check (`[?*[]` outside quotes; `$` followed by `[A-Za-z_@*#?!$0-9-]`, NOT `${`/`$(` — those are bashSecurity's substitution patterns; literal inside SQ, expands inside DQ) → try flag-parsing tier → fall through to regex tier where a match still fails if git `-c`/`--exec-path`/`--config-env` appear (code-exec config injection). Anchoring lesson baked into the list: `node --version` previously matched via a suffix-permitting shared regex until `node -v --run <task>` executed package.json scripts — now exact-match only.

**Invariant:** (1) Quote-tracking must model bash exactly or every downstream regex is advisory: backslash is literal inside single quotes. (2) A hand-written regex is a second validation plane with its own threat model — the `$` guard exists precisely because the token-level check doesn't reach this tier. (3) Version-check regexes must be FULLY anchored: any suffix permission plus a tool that processes later flags first equals arbitrary script execution. (4) Post-filter known code-exec flags (-c etc.) even after a regex match — defense in depth on the most-abused binary.

**Probe:** no upstream tests reachable — coverage caveat. Pins from repo root: `grep -nF 'uniq --skip-chars=0$_' src/tools/BashTool/readOnlyValidation.ts` → :1583,:1585,:1700; `grep -nF "Node processes --run before -v" src/tools/BashTool/readOnlyValidation.ts` → :1534.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "containsUnquotedExpansion single quote escaped", limit: 6 });
// → containsUnquotedExpansion :1600-1669 line-exact rank #3 (with shellQuote twins)
```

## Verdict
Adopt the two-tier structure (flag-table first, regex fallback for trivial commands) and the quote-state tracker verbatim. Adapt the command name lists to your host's userland. Omit the claude-specific `-h` entries.
