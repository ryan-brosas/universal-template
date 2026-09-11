<!-- capsule-v2 -->
# PS allowlist removals — which "read-only-looking" cmdlets were deliberately kicked out, and why does removal beat flag-filtering?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When a cmdlet's safe subset cannot be expressed as a flag list (pipeline input bypasses args entirely), what is the correct allowlist action?

## Remove the entry; prompt; document the PoC inline
**Path/Symbol:** `src/tools/PowerShellTool/readOnlyValidation.ts` `CMDLET_ALLOWLIST` removal comments: select-xml XXE (:321-326), test-json $ref fetch (:339-343), get-command/get-help module-autoload (:439-457), get-wmiobject/get-ciminstance network classes (:661-669), get-dnsclientcache -CimSession exclusion (:610-614), get-winevent -FilterXml/-FilterHashtable (:638-656), netsh never-added rationale (:793-800), man/help alias cleanup (:877-880), get-clipboard never-included note (:389-391), file `-C` magic-db write (:809-811).
**Signature:** N/A — negative space of `CMDLET_ALLOWLIST` + per-entry `safeFlags` exclusions.
**Data Shape:** Each removal comment names the attack shape; some entries survive with DANGEROUS PARAMS omitted from safeFlags instead.

### Decisive source
```ts
// SECURITY: Get-Command REMOVED from allowlist. -Name (positional 0,
// ValueFromPipeline=true) triggers module autoload which runs .psm1 init
// code. Chain attack: pre-plant module in PSModulePath, trigger autoload.
// Previously tried removing -Name/-Module from safeFlags + rejecting
// positional StringConstant, but pipeline input (`'EvilCmdlet' | Get-Command`)
// bypasses the callback entirely since args are empty. Removal forces
// prompt. Users who need it can add explicit allow rule.
```

**Flow:** decision ladder: (1) if dangerous surface is reachable through POSITIONAL/PIPELINE input that flag lists cannot see ⇒ remove entry entirely (autoload chain, WMI ping exfil, XXE); (2) if only specific FLAGS are dangerous ⇒ keep entry minus those flags (-FilterXml, -CimSession); (3) if grammar is too complex to enumerate safely after repeated denylist gaps ⇒ never add (netsh: 3 rounds of PR #22060 fixes each revealed another gap; route stays because `route print` is single-verb). Alias hygiene follows entries: removing get-help requires also removing its man/help aliases or lookupAllowlist resolves them to nothing-promptable confusion.
**Invariant:** safeFlags validates EXPLICIT flags only — any cmdlet whose hazard binds via pipeline/positional binding must not rely on it. Removal is user-respectful: explicit allow rules still work; the default flips from trust to prompt.
**Probe:** `grep -nF "select-xml REMOVED" src/tools/PowerShellTool/readOnlyValidation.ts` and `grep -cF "REMOVED" src/tools/PowerShellTool/readOnlyValidation.ts` and `grep -nF "netsh: intentionally NOT allowlisted" src/tools/PowerShellTool/readOnlyValidation.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "CMDLET_ALLOWLIST safeFlags SECURITY removed", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves `isAllowlistedCommand`/`lookupAllowlist` region :1088-1516 carrying all removal comments)*

## Verdict
Adopt the three-rung ladder (remove / trim flags / never-add) and inline-PoC documentation style for every exclusion. Adapt the specific cmdlets to your surface. Omit PR numbers except where they carry the lesson. Coverage caveat: probes deterministic; no upstream tests.
