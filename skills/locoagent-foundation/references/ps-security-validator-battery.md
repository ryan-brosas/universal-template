<!-- capsule-v2 -->
# PS security validator battery — in what ORDER do 24 AST validators run, and why does every one of them return only ask?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How do you structure a PowerShell command-security scan so each attack vector (iex, dynamic names, encoded commands, cradles, COM, WMI spawn, CLM types…) has exactly one decisive validator, and what is the battery's only possible output?

## Ordered ask-only battery; passthrough means nothing matched
**Path/Symbol:** `src/tools/PowerShellTool/powershellSecurity.ts`:`powershellCommandIsSafe` (:1042-1090) with the ordered `validators` array (:1054-1079); helpers `checkDynamicCommandName` (:143-160), `checkStartProcess` (:550-633), `checkComObject` (:343-429), `checkDangerousFilePathExecution` (:452-487), `checkForEachMemberName` (:499-534), `psExeHasParamAbbreviation` (:83-100).
**Signature:** `function powershellCommandIsSafe(_command: string, parsed: ParsedPowerShellCommand): { behavior: 'passthrough'|'ask'|'allow'; message?: string }`.
**Data Shape:** Input requires a SUCCESSFUL parse (`!parsed.valid ⇒ { behavior:'ask', message:'Could not parse command for security analysis' }` immediately). Output is only `'ask' | 'passthrough'` — the engine at the call site converts ask into a decision; allow never originates here.

### Decisive source
```ts
const validators = [
  checkInvokeExpression,
  checkDynamicCommandName,
  checkEncodedCommand,
  checkPwshCommandOrFile,
  checkDownloadCradles,
  checkDownloadUtilities,
  checkAddType,
  checkComObject,
  checkDangerousFilePathExecution,
  checkInvokeItem,
  checkScheduledTask,
  checkForEachMemberName,
  checkStartProcess,
  checkScriptBlockInjection,
  // ...AST-only checks: SubExpressions, ExpandableStrings, Splatting,
  // StopParsing, MemberInvocations, TypeLiterals(CLM), EnvVarManipulation,
  // ModuleLoading, RuntimeStateManipulation, WmiProcessSpawn
]
for (const validator of validators) {
  const result = validator(parsed)
  if (result.behavior === 'ask') {
    return result
  }
}
return { behavior: 'passthrough' }
```

**Flow:** first-match-wins over the array; each validator scans `getAllCommands(parsed)` (pipeline commands ∪ nestedCommands from control flow / ParamBlock / traps). Key vectors: dynamic command names are caught by ALLOWLISTING `elementTypes[0] === 'StringConstant'` rather than denylisting dynamic types (`& ('iex','x')[0] payload` maps to 'Other' and would evade a `=== 'Variable'` check); `-Verb RunAs` elevation is caught three ways (space syntax + children[] structural colon-bound + regex fallback for quoting like `-Verb:'RunAs`'); Start-Process targeting any PS executable asks because the nested invocation is unvalidatable by construction; positional StringConstant args on `ForEach-Object`/filepath-execution cmdlets ask because parameter-set resolution binds them to -MemberName/-FilePath with NO scriptblock in the tree.
**Invariant:** The battery can never deny and never allow — a clean pass-through is not innocence, it just leaves the decision to later gates. Every parameter-matching helper goes through `psExeHasParamAbbreviation`, which normalizes `/`, en-dash, em-dash, horizontal-bar prefixes to ASCII `-` before abbreviation matching (PowerShell's tokenizer accepts all four plus PS5.1's `/`; bare `commandHasArgAbbreviation` let `Start-Process foo –Verb RunAs` bypass). Unambiguous minimum prefixes are load-bearing data (`-com` for -ComObject because `-co` collides with -Confirm on 5.1; `-t` for -TypeName; `-m` for -MemberName).
**Probe:** `grep -nF "const validators = [" src/tools/PowerShellTool/powershellSecurity.ts` and `grep -cF "psExeHasParamAbbreviation(" src/tools/PowerShellTool/powershellSecurity.ts` → `7` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "powershellCommandIsSafe validators", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ask-only-battery shape (security scanning informs prompts; hard decisions live in the permission engine), the ordered vector list as a porting checklist, and the alt-prefix normalization wrapper. Adapt the specific cmdlet/exe name sets to your threat model. Omit upstream finding numbers. Coverage caveat: no unit tests in-repo; graph confirms `powershellCommandIsSafe` :1042-1090 line-exact rank#1.
