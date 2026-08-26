<!-- capsule-v2 -->
# PS parse-failed fallback scan — when pwsh dies mid-permission-check, how do deny rules still fire on fragments the AST never saw?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What raw-text triage replaces AST-based sub-command deny checking when parsing fails (oversized command, missing pwsh, timeout)?

## Backtick-aware fragment splitter feeding the SAME prefix-deny matcher
**Path/Symbol:** `src/tools/PowerShellTool/powershellPermissions.ts` parse-failed branch (:764-874): `PS_ASSIGN_PREFIX_RE` (:62), backtick collapse+strip → split `[;|\n\r{}()&]+` (:784-787), full-command skip conditions (:792-801), assignment/dot-source/quote normalization loop (:816-824), parse-independent dangerous-removal hard-deny (:833-840), per-fragment prefix-deny match (:841-852).
**Signature:** inline in `powershellToolHasPermission`; operates purely on `command: string` after `parsed.valid === false`.
**Data Shape:** Fragments are raw strings; each runs through the same `matchingRulesForInput(..., 'prefix')` used by the parsed path.

### Decisive source
```ts
// SECURITY: backtick is PS escape/line-continuation, NOT a separator.
// Splitting on it would fragment `Invoke-Ex`pression` into non-matching
// pieces. Instead: collapse backtick-newline (line continuation) so
// `Invoke-Ex`<nl>pression` rejoins, strip remaining backticks (escape
// chars — ``x → x), then split on actual statement/grouping separators.
const backtickStripped = command
  .replace(/`[\r\n]+\s*/g, '')
  .replace(/`/g, '')
for (const fragment of backtickStripped.split(/[;|\n\r{}()&]+/)) {
```

**Flow:** for each non-empty fragment: skip re-checking the FULL command only when it starts with a bare cmdlet name (no `$x =` assignment prefix, no `& `/`. ` operator) since step 2a already matched its raw text → strip nested assignment prefixes (`$x = $y = iex` → `iex`), invocation operators, and surrounding quotes from the first token → if canonicalized first token is `remove-item`, scan positional args through `isDangerousRemovalRawPath` for a parser-independent hard-deny of `/`, `~`, system paths → run prefix-deny rules against the normalized fragment.
**Invariant:** This is a deny-DOWNGRADE fix in an already-degraded state: false-positive denies inside string literals/comments are acceptable; missed denies are not. The generic parse-error ask still carries the deferred pre-parse ask's better decisionReason when one exists, and suggestions are suppressed (never persist invalid syntax).
**Probe:** `grep -nF "PS_ASSIGN_PREFIX_RE" src/tools/PowerShellTool/powershellPermissions.ts | head -2` and `grep -nF "backtickStripped.split(/[;|\\\\n\\\\r{}()&]+/)" src/tools/PowerShellTool/powershellPermissions.ts || grep -nF 'split(/[;|' src/tools/PowerShellTool/powershellPermissions.ts | head -1` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "fallback sub-command deny scan parse failed fragment", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves `powershellToolHasPermission` :639-1648 containing the whole branch)*

## Verdict
Adopt degraded-mode deny scanning (same matcher, conservative normalization) whenever your permission funnel depends on a parser that can be absent. Adapt the separator class and escape character to your shell. Omit bug-number lore. Coverage caveat: probes deterministic; no upstream tests.
