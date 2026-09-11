<!-- capsule-v2 -->
# PS safe-output migration — why did Format-Table stop being a name-only pipeline filter, and what replaced the set?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When a pipeline-tail cmdlet "just formats output," what hidden argument surface forces it out of name-only filtering and into arg-validated allowlisting?

## SAFE_OUTPUT_CMDLETS shrank to Out-Null; everything else moved to allowlist + argLeaksValue
**Path/Symbol:** `src/tools/PowerShellTool/readOnlyValidation.ts`:`SAFE_OUTPUT_CMDLETS` (:888-917, now ONLY `out-null`), `PIPELINE_TAIL_CMDLETS` (:931-943), `isAllowlistedPipelineTail` (:1052-1061); consumers at `getSubCommandsForPermissionCheck` (:582-585: nameType + zero-args required), `modeValidation.ts` (:327-332), `powershellPermissions.ts` step-5 loop (:1277-1287).
**Signature:** `function isSafeOutputCommand(name: string): boolean` (name-only via `resolveToCanonical`); `function isAllowlistedPipelineTail(cmd, originalCommand): boolean`.
**Data Shape:** SAFE_OUTPUT membership requires BOTH `nameType !== 'application'` AND `cmd.args.length === 0` at every consumer.

### Decisive source
```ts
const SAFE_OUTPUT_CMDLETS = new Set([
  'out-null',
  // NOT foreach-object / where-object / select-object / sort-object /
  // group-object / format-table / format-list / format-wide / format-custom /
  // measure-object — ALL accept calculated-property hashtables or script-block
  // predicates that evaluate arbitrary expressions at runtime ...
  // isSafeOutputCommand is a NAME-ONLY check — step-5 filters these out of
  // the approval loop BEFORE arg validation runs.
])
```

**Flow:** history: Format-*/Measure-*/Select-/Sort-/Group-/Where-Object and Out-String/Out-Host were name-only filters; security review found they all accept calculated-property hashtables (`about_Calculated_Properties`) and `-InputObject` leaks (`Get-Process | Out-String -InputObject $env:SECRET`). Migration: each moved to `CMDLET_ALLOWLIST` with `allowAllFlags: true` + `argLeaksValue` callback; `PIPELINE_TAIL_CMDLETS` + `isAllowlistedPipelineTail` preserve the skip-harmless-tail UX but route through full arg validation. Even surviving `out-null` is filtered only when zero-arg (`Out-Null -InputObject:(1 > /etc/x)` must NOT vanish from approvals).
**Invariant:** Name-only classification may only ever remove a command from approval when NO argument exists to validate; any args force the arg-level path. `ForEach-Object` is deliberately excluded even though its block commands ARE recursively scanned — non-command AST nodes inside blocks (assignments) are invisible to command walkers.
**Probe:** `python3 -c "import re;t=open('src/tools/PowerShellTool/readOnlyValidation.ts').read();m=re.search(r'const SAFE_OUTPUT_CMDLETS = new Set\(\[(.*?)\]\)',t,re.S);print([l.strip().rstrip(',') for l in m.group(1).splitlines() if l.strip() and not l.strip().startswith('//')])"` → prints `['out-null']` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "SAFE_OUTPUT_CMDLETS PIPELINE_TAIL_CMDLETS isAllowlistedPipelineTail", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the migration pattern (shrink the name-only set to provably-inert members; move the rest behind arg validation; keep a narrow tail-skip wrapper). Adapt member lists to your cmdlet surface but keep the calculated-properties rationale. Omit per-bug numbers. Coverage caveat: probes are deterministic pins; graph confirms `isAllowlistedPipelineTail` :1052-1061.
