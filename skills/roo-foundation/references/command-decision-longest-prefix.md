<!-- capsule-v2 -->
# command auto-approval decision kernel — longest-prefix-match, chain splitting, and the dangerous-substitution veto

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Given allow + deny prefix lists and a chained shell command, who wins — and what gets escalated to the human regardless of lists?

## Pure decision functions over parsed sub-commands
**Path/Symbol:** `src/core/auto-approval/commands.ts` — `containsDangerousSubstitution` :22, `findLongestPrefixMatch` :95, `isAutoApprovedSingleCommand` :124, `isAutoDeniedSingleCommand` :180, `getCommandDecision` :256 (entry), `getSingleCommandDecision` :340.
**Signature:** `getCommandDecision(command: string, allowedCommands: string[], deniedCommands?: string[]): "auto_approve" | "auto_deny" | "ask_user"`; `parseCommand` (from `src/shared/parse-command.ts`, shell-quote based) splits on `&& || ; | &` + newlines while respecting quotes/subshells.
**Data Shape:** prefixes are lowercase-compared startsWith patterns; `"*"` is a wildcard matching anything but counts as length 1 in comparisons.

### Decisive source
```ts
const decisions: CommandDecision[] = subCommands.map((cmd) => {
    // Remove simple PowerShell-like redirections (e.g. 2>&1) before checking
    const cmdWithoutRedirection = cmd.replace(/\d*>&\d*/, "").trim()
    return getSingleCommandDecision(cmdWithoutRedirection, allowedCommands, deniedCommands)
})
if (decisions.includes("auto_deny")) return "auto_deny"
// Require explicit user approval for dangerous patterns
if (containsDangerousSubstitution(command)) return "ask_user"
```

**Flow:** empty command → auto_approve; split into sub-commands; strip `\d*>&\d*` redirections per part; single decision matrix — only-allow → approve, only-deny → deny, BOTH → longer prefix wins, NEITHER → ask. Aggregation: any auto_deny denies the WHOLE chain; otherwise a dangerous-substitution hit on the FULL original string forces ask_user; all-approved → approve; else ask. Dangerous patterns: `${var@[PQEAa]}` expansion operators, `${var[=+-?]…}` with octal/hex/unicode escapes (`\140` backtick smuggling), `${!var}` indirect refs, here-string-with-substitution `<<<$(/backtick`, zsh process substitution `=(cmd)` (lookbehind-guarded so array assignment `var=(a b)` does NOT trip), zsh glob qualifiers `*(e:cmd:)`.
**Invariant:** ASYMMETRIC TIE-BREAK: equal-length allow vs deny matches resolve to DENY in `getSingleCommandDecision` (`longestAllowedMatch.length > longestDeniedMatch.length` strict) and in `isAutoDeniedSingleCommand` (`>=`) — fail-closed by construction. The substitution veto runs on the whole command AFTER chain parsing and cannot be downgraded by any list content: even an allowlisted command with `${var@P}` goes to ask_user. Redirection stripping prevents `git status 2>&1` from failing its own prefix match on the `2>&1` tail.
**Probe:** `grep -c '@\[PQEAa\]' src/core/auto-approval/commands.ts` → 1; `grep -c 'longestDeniedMatch.length >= longestAllowedMatch.length' src/core/auto-approval/commands.ts` → 1; `grep -cF '\d*>&\d*' src/core/auto-approval/commands.ts` → 1; `grep -c 'includes("auto_deny")' src/core/auto-approval/commands.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "getCommandDecision findLongestPrefixMatch containsDangerousSubstitution", limit: 10 });
```
(live-verified rank#1–3 exact).

## Verdict
Adopt the pure-function trio shape, the any-denial-blocks-all aggregation, the strict longer-prefix tie-break, and the full-string substitution veto. Adapt pattern families to your host's shells. Direct test: `src/core/auto-approval/__tests__/commands.spec.ts` (zsh-array false-positive regression describe :4, node-e one-liner regression :41/:88, arrow-function non-flags :49, true-positive set :63, integration :85).
