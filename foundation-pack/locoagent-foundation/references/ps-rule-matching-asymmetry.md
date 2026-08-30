<!-- capsule-v2 -->
# PS rule matching asymmetry — how does one matcher serve deny (over-match welcome) and allow (over-match fatal) with canonical alias resolution?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do user rules like `deny Remove-Item:*` catch `rm`, and why is the same widening forbidden on allow?

## Behavior-parameterized stripping + dual-form command matching
**Path/Symbol:** `src/tools/PowerShellTool/powershellPermissions.ts`:`filterRulesByContentsMatchingInput` (:170-333) incl. `stripModulePrefixForRule` (:189-194), whitespace-normalized `canonicalCommand` (:201-215), exact/prefix/wildcard canonical branches (:265-328); consumers `powershellToolCheckExactMatchPermission` (:385-430, matchMode 'exact') and `powershellToolCheckPermission` (:435-514, 'prefix').
**Signature:** `function filterRulesByContentsMatchingInput(input: { command: string }, rules: Map<string, PermissionRule>, matchMode: 'exact'|'prefix', behavior: 'deny'|'ask'|'allow'): PermissionRule[]`.
**Data Shape:** Rules: exact (`PowerShell(cmd)`), prefix (`PowerShell(cmd:*)`), wildcard (`PowerShell(cmd * x)`). Matching is case-insensitive end to end.

### Decisive source
```ts
// SECURITY: stripModulePrefix on RULE names widens the
// secondary-canonical match — a deny rule `Module\\Remove-Item:*` blocking
// `rm` is the intent (fail-safe over-match), but an allow rule
// `ModuleA\\Get-Thing:*` also matching `ModuleB\\Get-Thing` is fail-OPEN.
// Deny/ask over-match is fine; allow must never over-match.
function stripModulePrefixForRule(name: string): string {
  if (behavior === 'allow') {
    return name
  }
  return stripModulePrefix(name)
}
```

**Flow:** split input into raw first token + rest → normalize rest's leading whitespace to ONE space (`rm\t./x` must hit prefix rule `Remove-Item:*`, which matches via literal `prefix + ' '`) → build canonicalCommand by resolving the token through `resolveToCanonical` → each rule matched against BOTH raw and canonical forms; additionally the RULE's own name is canonicalized (deny/ask only) so `deny rm:*` also blocks `Remove-Item secret.txt`. Exact-rule branch compares rule-rest vs input-rest after identical normalization.
**Invariant:** The asymmetry IS the design: every widening transformation is gated on behavior. Also structural: exact allow of a compound never bypasses sub-command denies because exact-allow enters decisions[] AFTER the per-sub-command loop pushed its denies (collect-then-reduce ordering).
**Probe:** `grep -nF "Deny/ask over-match is fine; allow must never over-match" src/tools/PowerShellTool/powershellPermissions.ts` → :188 and `grep -n "s+/, ' ')" src/tools/PowerShellTool/powershellPermissions.ts | head -1` → :214 (the canonicalCommand normalization site; anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "filterRulesByContentsMatchingInput canonical wildcard prefix", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt behavior-gated widening for any shared rule matcher; adopt whitespace normalization before prefix comparison. Adapt rule grammar tokens. Omit shared-module plumbing (`shellRuleMatching`). Coverage caveat: probes deterministic; no upstream tests.
