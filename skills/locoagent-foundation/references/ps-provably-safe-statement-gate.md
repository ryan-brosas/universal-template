<!-- capsule-v2 -->
# PS isProvablySafeStatement fail-closed shape gate — which statement ASTs may an auto-allow trust, and what closes the invisible-content hole?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When per-sub-command approval comes up empty, how do you prove nothing unverifiable slipped past the CommandAst walk before auto-allowing the whole pipeline?

## Pipeline-of-CommandAsts is the ONLY trusted statement shape; untracked statements re-prompt
**Path/Symbol:** `src/tools/PowerShellTool/readOnlyValidation.ts`:`isProvablySafeStatement` (:1072-1082); enforcement `powershellPermissions.ts`: push-tracked `statementsSeenInLoop` (:1430-1432, add sites :1452/:1486/:1499/:1574) + fail-closed sweep (:1593-1597) + scriptblock final gate (:1599-1617).
**Signature:** `function isProvablySafeStatement(stmt: ParsedStatement): boolean`.
**Data Shape:** True ONLY for `statementType === 'PipelineAst'` with ≥1 command and EVERY element `elementType === 'CommandAst'`.

### Decisive source
```ts
for (const stmt of parsed.statements) {
  if (!isProvablySafeStatement(stmt) && !statementsSeenInLoop.has(stmt)) {
    subCommandsNeedingApproval.push(stmt.text)
  }
}
// ...and when the approval list ends up empty:
if (deriveSecurityFlags(parsed).hasScriptBlocks) {
  return { behavior:'ask', /* block content cannot be verified */ }
}
return { behavior: 'allow', reason: 'All pipeline commands are individually allowed' }
```

**Flow:** step-5 iterates sub-commands; statements get marked seen ONLY on PUSH (never loop-entry — if every sub-command `continue`d via user allow rules, marking-at-entry would let bare `$env:SECRET` inside control flow auto-allow silently; documented attack: approve Get-Process then `if ($true) { Get-Process; $env:SECRET }`). After the loop, any statement never proven-safe AND never pushed joins the approval list. Empty list ⇒ auto-allow EXCEPT pipelines of output-formatting cmdlets carrying scriptblocks (`Where-Object {$true} | Sort-Object {$env:PATH='evil'}` — assignments nested in blocks are invisible to getAllCommands and hasAssignments is top-level-only).
**Invariant:** Filtering IS auto-allowing — the two halves (shape whitelist + push-tracking) must both hold or the empty-list fast path becomes an exfiltration primitive. New AST types fail closed by construction because the gate enumerates one true-shape rather than denylisting shapes.
**Probe:** `grep -nF "stmt.commands.length === 0" src/tools/PowerShellTool/readOnlyValidation.ts` → :1077 and `grep -cF "statementsSeenInLoop.add" src/tools/PowerShellTool/powershellPermissions.ts` → `4` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", name_pattern: "isProvablySafeStatement", limit: 5, fields: ["signature", "name", "file"] });
```
*(BM25 query-mode returns noise for this symbol; name_pattern resolves Function :1072-1082 exactly)*

## Verdict
Adopt the single-true-shape gate plus track-on-push discipline for ANY sub-command approval collector. Adapt to your AST taxonomy. Omit historical bug ids. Coverage caveat: probes deterministic; graph confirms `isProvablySafeStatement` :1072-1082 (name_pattern mode).
