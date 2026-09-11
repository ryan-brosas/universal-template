<!-- capsule-v2 -->
# Sed denylist battery & constraint gate — paranoid rejection of everything the two-pattern grammar can't name

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** Even after an allowlist match, what denylist must run — and how do you reject Unicode homoglyphs, alternate delimiters, and malformed s-commands without a full parser?

## Path/Symbol
**Path/Symbol:** `src/tools/BashTool/sedValidation.ts` — `containsDangerousOperations` (:473-629): non-ASCII rejection (:484-486), braces/newlines (:488-496), `#` comment vs `s#` delimiter discrimination (:498-504), negation `!` (:506-511), GNU step addresses `~` (:513-517), bare/offset commas (:519-527), backslash-delimiter tricks (:529-534), escaped-slash+write (:536-539), malformed-s checks incl. the PARANOID tail (:541-563), positional w/W battery (:565-579), e/E battery (:581-595), substitution-flag w/W/e/E scan with ANY-delimiter match `/s([^\\\n]).*?\1.*?\1(.*?)$/` (:597-613), y-command paranoia (:615-626); export `checkSedConstraints` (:644-684).
**Signature:** `containsDangerousOperations(expression: string): boolean`; `checkSedConstraints(input: { command: string }, toolPermissionContext: ToolPermissionContext): PermissionResult`.
**Data Shape:** operates per-expression AFTER quote extraction; returns boolean (true = dangerous). checkSedConstraints: 'ask' on any disallowed sed subcommand, 'passthrough' otherwise.

### Decisive source
```ts
// CONSERVATIVE REJECTIONS: Broadly reject patterns that could be dangerous
// When in doubt, treat as unsafe

// Reject non-ASCII characters (Unicode homoglyphs, combining chars, etc.)
// Examples: ｗ (fullwidth), ᴡ (small capital), w̃ (combining tilde)
// eslint-disable-next-line no-control-regex
if (/[^\x01-\x7F]/.test(cmd)) {
  return true
}
```
```ts
// PARANOID: Reject any command starting with 's' that ends with dangerous chars (w, W, e, E)
// and doesn't match our known safe substitution pattern. This catches malformed s commands
// with non-slash delimiters that might be trying to use dangerous flags.
if (/^s./.test(cmd) && /[wWeE]$/.test(cmd)) {
  const properSubst = /^s([^\\\n]).*?\1.*?\1[^wWeE]*$/.test(cmd)
  if (!properSubst) {
    return true
  }
}
```

**Flow:** allowlist match is NECESSARY but not sufficient → every expression runs the battery: non-ASCII ⇒ dangerous (homoglyph commands like fullwidth ｗ); `{}` blocks; comments (`#` not preceded by `s`, so `s#pat#repl#` survives); `!` negation; step addresses; bare `,`; offset commas; backslash delimiter tricks; escaped-slash-then-w; address-position w/W and e/E batteries (simplified regexes to dodge CodeQL exponential backtracking); any-delimiter s-command whose trailing flags contain w/W/e/E; finally ANY y-command plus ANY w/W/e/E in the expression. Gate: acceptEdits mode still routes through this battery — it only widens the ALLOWLIST side.

**Invariant:** (1) Denylist complements, never replaces, the allowlist — both must pass ("defense-in-depth" comment at the call site). (2) Non-ASCII = dangerous is the cheapest homoglyph defense: sed commands have no legitimate non-ASCII need. (3) Delimiter generality cuts both ways: POSIX allows almost any delimiter, so the flag-scan uses backreference matching (`\1`) instead of hardcoding `/`, and anything not fitting the well-formed shape loses. (4) When-in-doubt-reject is explicit policy: complexity ({}, newlines, step addresses) is itself the threat because it exceeds what the reviewer can enumerate.

**Probe:** no upstream tests reachable — coverage caveat. Pins from repo root: `grep -nF "Dangerous flag combination detected" src/tools/BashTool/sedValidation.ts` → :399 (throw inside extractSedExpressions); `grep -nF "checkSedConstraints(input, toolPermissionContext)" src/tools/BashTool/bashPermissions.ts` → :1142 (consumer wiring).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "containsDangerousOperations checkSedConstraints", limit: 4 });
// → containsDangerousOperations :473-629 + checkSedConstraints :644-684 line-exact (total:2)
```

## Verdict
Adopt the battery ordering and the paranoid s/y tails verbatim. Adapt only the mode name in checkSedConstraints. Omit nothing — each regex cites its attack class inline.
