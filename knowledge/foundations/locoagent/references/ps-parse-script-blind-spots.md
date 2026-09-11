<!-- capsule-v2 -->
# PS parse-script blind spots — which AST regions are invisible to block-statement walking, and how does each get its own escape hatch?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** What does the PowerShell AST contain that a Process-BlockStatements walker never sees, and what must every consumer add back?

## Four blind regions: ParamBlock, using/#Requires, traps, deep redirections
**Path/Symbol:** `src/utils/powershell/parser.ts` PARSE_SCRIPT_BODY: SECURITY comment + ParamBlock FindAll (:282-295, :530-545), UsingStatements/ScriptRequirements emission (:547-548), Trap handling (:492-521); TS consumers: `powershellPermissions.ts` using/#Requires asks (:940-971); `powershellSecurity.ts` hasStopParsing check.
**Signature:** script-level: `$ast.ParamBlock`, `$ast.UsingStatements`, `$ast.ScriptRequirements`, `$Block.Traps` — all SIBLINGS of or adjacent to the named blocks.
**Data Shape:** `ParsedPowerShellCommand.hasUsingStatements?: boolean`, `hasScriptRequirements?: boolean`; nestedCommands carry ParamBlock/trap commands; `hasStopParsing` from token stream (PS7 MinusMinus kind vs PS5.1 Generic with dash-unicode normalization).

### Decisive source
```text
SECURITY — top-level ParamBlock: ScriptBlockAst.ParamBlock is a SIBLING of
the named blocks ..., so Process-BlockStatements never reaches it. Commands
inside param() default-value expressions ... were invisible to every downstream
check. PoC:
  param($x = (Remove-Item /)); Get-Process   → only Get-Process surfaced
  param([ValidateScript({rm /;$true})]$x='t') → rm invisible, runs on bind
```

**Flow:** ParamBlock gets a dedicated FindAll emitting a synthetic `ParamBlockAst` statement ONLY when it contains commands/redirections/security patterns (avoids noise for plain declarations). Function-level param() is already covered because FindAll on FunctionDefinitionAst recurses descendants — only the SCRIPT-level block was gapped. `using module`/`using assembly`/`#Requires -Modules` are emitted as booleans and converted into ASKS by the permission engine before any allowlist evaluation (decoy Get-Process would otherwise fill subCommands and auto-allow).
**Invariant:** Any new consumer that walks statements MUST also consult the boolean flags and nestedCommands — trusting statement.commands alone reopens all four gaps. The stop-parsing token needs TWO token-kind branches because PS5.1 and PS7 tokenize `--%` differently.
**Probe:** `grep -nF "if ($ast.ParamBlock)" src/utils/powershell/parser.ts` and `grep -nF "hasUsingStatements" src/tools/PowerShellTool/powershellPermissions.ts | head -1` and `grep -cF "Process-BlockStatements -Block" src/utils/powershell/parser.ts` → `5` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "ParamBlock UsingStatements ScriptRequirements blind", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves parsePowerShellCommandImpl :1136-1261 and the transform plane carrying the flags)*

## Verdict
Adopt the audit habit: enumerate what your walker CANNOT reach and give each region a typed signal consumers must honor. Adapt to your parser's grammar version quirks. Omit PoC exploit text beyond the documented pair. Coverage caveat: probes deterministic; no upstream tests.
