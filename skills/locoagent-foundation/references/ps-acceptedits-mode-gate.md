<!-- capsule-v2 -->
# PS acceptEdits mode gate — how can a write-auto-allow mode survive scriptblocks, expression sources, and unvalidatable element types?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When the user's mode says "auto-approve file edits," which AST shapes must still force approval before Set-Content runs without a prompt?

## Security-flag veto + per-command whitelist + argLeaksValue, then 4-cmdlet allow
**Path/Symbol:** `src/tools/PowerShellTool/modeValidation.ts`:`checkPermissionMode` (:132-404): security-flag veto (:165-180), compound cd/link guards (:206-242), non-CommandAst source guard (:246-268 — documented as load-bearing for THREE cases), nameType gate (:273-278), elementTypes whitelist + colon-bound metachar check (:297-319), tail skip (:327-332), `ACCEPT_EDITS_ALLOWED_CMDLETS` = {set-content, add-content, remove-item, clear-content} (:33-38), final argLeaksValue (:347-352); nested-commands mirror (:356-392).
**Signature:** `function checkPermissionMode(input: { command: string }, parsed: ParsedPowerShellCommand, ctx: ToolPermissionContext): PermissionResult` — `'allow' | 'passthrough'` only.
**Data Shape:** Auto-allow set is deliberately Tier-simple (positional-0 = -Path cmdlets); complex-binding writes (new-item/copy-item/move-item) fall through to ask and get their path validation via CMDLET_PATH_CONFIG instead.

### Decisive source
```ts
// SECURITY: This guard is load-bearing for THREE cases. Do not narrow it.
// 1. Expression pipeline sources (designed): '/etc/passwd' | Remove-Item ...
// 2. Control-flow statements (accidental but relied upon):
//    foreach ($x in ...) { Remove-Item $x } ...
// 3. Non-PipelineAst redirection coverage (accidental): cmd && cmd2 > /tmp ...
if (cmd.elementType !== 'CommandAst') {
  return { behavior: 'passthrough', message: `Pipeline contains expression source ...` }
}
```

**Flow:** bypass/dontAsk modes skip; non-acceptEdits skip; invalid parse skips → ANY security flag (subexpression/scriptblock/member/splatting/assignment/stop-parsing/expandable-string) vetoes → compound containing cd or link-create vetoes → per command: synthetic/expression elements veto, application names veto, args must be StringConstant/Parameter ONLY with colon-bound values free of `$(@{[` metachars → pipeline-tail transformers skipped via isAllowlistedPipelineTail → remaining commands must be in the 4-cmdlet set AND pass argLeaksValue (catches `-Value @{k='payload' > ~/.bashrc}` HashtableAst 'Other') → allow.
**Invariant:** Mode auto-allow is a NARROWING of the permission engine, never a parallel authority: every veto returns passthrough so normal gates decide. The accidental-but-load-bearing reliance on synthetic CommandExpressionAst entries for control flow means isReadOnlyCommand's identically-shaped guard must evolve in lockstep.
**Probe:** `grep -nF "ACCEPT_EDITS_ALLOWED_CMDLETS = new Set([" src/tools/PowerShellTool/modeValidation.ts` and `grep -cF "behavior: 'passthrough'" src/tools/PowerShellTool/modeValidation.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "checkPermissionMode acceptEdits securityFlags expression source", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the veto-first ordering and the tiny auto-allow surface. Adapt the 4-cmdlet set to your product's edit story. Omit BashTool parity cross-refs. Coverage caveat: probes deterministic; no upstream tests.
