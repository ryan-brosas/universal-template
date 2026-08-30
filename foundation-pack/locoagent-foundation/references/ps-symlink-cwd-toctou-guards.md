<!-- capsule-v2 -->
# PS symlink/cwd TOCTOU compound guards — which compound-command shapes invalidate every relative path the validator just checked?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How does the permission engine neutralize compounds that change path-resolution state between validation and execution (cd, PSDrive, symlink creation)?

## Three namespace-changers detected once; every downstream gate consumes the flags
**Path/Symbol:** `src/tools/PowerShellTool/readOnlyValidation.ts`:`isCwdChangingCmdlet` (:1017-1033 — Set/Push/Pop-Location + New-PSDrive + Windows-only ndr/mount aliases), `modeValidation.ts`:`isSymlinkCreatingCommand` (:82-117 — New-Item `-ItemType`/`-Type` ∈ {symboliclink, junction, hardlink} with abbreviation/unicode-dash/colon-bound/quote+backtick normalization, min prefixes `-it`/`-ty`); flags computed at `powershellPermissions.ts` :1127-1138; consumers: modeValidation cd+write and link guards (:206-242), isReadOnlyCommand cd guard (:1223-1234), checkPathConstraints threading (:1271-1276), step-5 skip gates (:1523-1531, :1554).
**Signature:** `function isCwdChangingCmdlet(name: string): boolean`; `function isSymlinkCreatingCommand(cmd: { name: string; args: string[] }): boolean`.
**Data Shape:** Both flags require `allSubCommands.length > 1` (standalone `Set-Location ./sub` is not a TOCTOU risk — no later statement resolves against stale cwd).

### Decisive source
```ts
// SECURITY: NO cd-to-CWD no-op exclusion. A previous iteration excluded
// `Set-Location .` as a no-op, but the "first non-dash arg" heuristic used
// to extract the target is fooled by colon-bound params:
// `Set-Location -Path:/etc .` — real target is /etc, heuristic sees `.`,
// exclusion fires, bypass. ... Any cd-family cmdlet in the compound sets
// this flag, period.
const hasSymlinkCreate =
  allSubCommands.length > 1 &&
  allSubCommands.some(({ element }) => isSymlinkCreatingCommand(element))
```

**Flow:** detect once per compound → cd∧git ⇒ ask (bare-repo attack); link-create ⇒ suppress ALL auto-allow paths (user-rule continue, allowlist shortcut, acceptEdits) because a read THROUGH a just-created link (`Get-Content ./link/passwd`) is as dangerous as a write; cd ⇒ checkPathConstraints forces ask for ANY path operation in the compound while still honoring deny rules via firstAsk ordering (deny > ask); isReadOnlyCommand refuses cd-compounds entirely. Rejected alternative documented: simulating cwd through the statement chain (Push/Pop stacks, no-arg-cd-to-home, conditional execution) — too many semantics to model, so approval wins.
**Invariant:** Reads get the same protection as writes (finding #27: `Set-Location ~; Get-Content ./.ssh/id_rsa` resolves `.ssh/id_rsa` against the STALE validator cwd and dodges Read(~/.ssh/**)). The cd-to-CWD special case must never return — colon-bound params defeat any first-non-dash-arg target heuristic.
**Probe:** `grep -nF "LINK_ITEM_TYPES = new Set(['symboliclink', 'junction', 'hardlink'])" src/tools/PowerShellTool/modeValidation.ts` and `grep -nF "canonical === 'new-psdrive'" src/tools/PowerShellTool/readOnlyValidation.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "isSymlinkCreatingCommand ItemType Junction", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt compute-once-consume-everywhere flag architecture for resolution-state changers, the reads-too rule, and the no-special-case ruling on cd-to-CWD. Adapt the cmdlet lists to your shell. Omit finding numbers. Coverage caveat: probes deterministic; graph confirms `isSymlinkCreatingCommand` :82-117 rank#1.
