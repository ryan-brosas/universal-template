<!-- capsule-v2 -->
# PS path-validation config table — how do you extract filesystem paths from cmdlet invocations whose parameter grammars you cannot fully know?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** Given ~30 path-taking PowerShell cmdlets with overlapping parameter sets, how do you extract every real path while guaranteeing unknown parameters fail closed?

## CMDLET_PATH_CONFIG three-list grammar + unknown-param fail-safe
**Path/Symbol:** `src/tools/PowerShellTool/pathValidation.ts`:`CMDLET_PATH_CONFIG` (:124-765), `extractPathsFromCommand` (:1304-1508), `matchesParam` (:772-782), `hasComplexColonValue` (:793-803); shared vocab `commonParameters.ts` (`COMMON_SWITCHES`/`COMMON_VALUE_PARAMS`, merged at :1323-1324 to break an import cycle).
**Signature:** `function extractPathsFromCommand(cmd: ParsedCommandElement): { paths: string[]; operationType: 'read'|'write'|'create'; hasUnvalidatablePathArg: boolean; optionalWrite: boolean }`.
**Data Shape:** Per-cmdlet entry: `operationType`, `pathParams` (values ARE paths), `knownSwitches` (consume nothing), `knownValueParams` (consume a non-path value), plus optional `leafOnlyPathParams` (New-Item -Name: leaf-only, resolved against ANOTHER param — non-leaf values flag unvalidatable), `positionalSkip` (iwr positional-0 is a URL), `optionalWrite` (iwr/irm write only with -OutFile). All names lowercase-with-dash; matching allows unambiguous PS prefixes (`matchesParam`: entry startsWith given prefix).

### Decisive source
```ts
} else {
  // Unknown parameter — we do not understand this invocation.
  // SECURITY: This is the structural fix for the KNOWN_SWITCH_PARAMS
  // whack-a-mole. Rather than guess whether this param is a switch
  // (and risk swallowing a positional path) ... we flag the whole command.
  hasUnvalidatablePathArg = true
  if (colonIdx > 0) {
    const rawValue = arg.substring(colonIdx + 1)
    if (!hasComplexColonValue(rawValue)) {
      paths.push(rawValue)  // deny rules still get their shot at ask-level
    }
  }
}
```

**Flow:** classify each arg via AST elementTypes (`isPowerShellParameter`; unicode-dash-proof) → route by list membership → colon-syntax values checked for complexity markers (`,`/`(`/`[`/backtick/`@(`/`@{`/`$`) which mask runtime paths ⇒ unvalidatable; else extracted → positionals become paths after `positionalSkip` → write cmdlets extracting ZERO paths force ask (nothing validated to write) unless `optionalWrite`.
**Invariant:** Any parameter outside the three lists means the invocation is NOT understood ⇒ overall ask, but its colon-bound simple value is still pushed into `paths[]` so explicit deny rules fire at ask level rather than degrading to generic prompt. Dual-path cmdlets (`copy-item`/`move-item` -Path + -Destination) mark both as write so both hit Edit denies — blunt but strictly safer than extracting neither.
**Probe:** `grep -cF "operationType: 'write'" src/tools/PowerShellTool/pathValidation.ts` and `grep -nF "hasUnvalidatablePathArg = true" src/tools/PowerShellTool/pathValidation.ts | wc -l` → `6` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "extractPathsFromCommand CMDLET_PATH_CONFIG unknown parameter", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the declarative three-list grammar + unknown-param fail-safe as THE pattern for per-command path extraction. Adapt the table contents per platform docs; keep `-pspath`/`-lp` runtime aliases in pathParams or colon syntax traps values. Omit Get-Command-derived provenance notes. Coverage caveat: probes deterministic; graph confirms `extractPathsFromCommand` :1304-1508 rank#1.
