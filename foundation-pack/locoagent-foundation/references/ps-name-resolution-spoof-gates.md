<!-- capsule-v2 -->
# PS name resolution spoof gates — which name string do the security validators actually match on, and who is allowed to have stripped it?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** When a porter strips module prefixes / quotes / PATHEXT from a command name, which copy of the name must feed allowlist matching vs deny-rule matching, and what unicode/path spoofs force the raw form to win?

## nameType from the RAW name; stripped name only for deny symmetry
**Path/Symbol:** `src/utils/powershell/parser.ts`:`transformCommandAst` (:830-935), `classifyCommandName` (:800-810), `stripModulePrefix` (:814-826), `COMMON_ALIASES` (:1326-1452); `src/tools/PowerShellTool/readOnlyValidation.ts`:`resolveToCanonical` (:984-996).
**Signature:** `function classifyCommandName(name: string): 'cmdlet'|'application'|'unknown'`; `function stripModulePrefix(name: string): string`; `function resolveToCanonical(name: string): string`.
**Data Shape:** `element.nameType` is computed from the RAW first token BEFORE stripping; `element.name` carries the stripped, quote-free name used for deny-rule matching.

### Decisive source
```ts
// SECURITY: nameType MUST be computed from the raw name (before
// stripModulePrefix). classifyCommandName('scripts\\Get-Process') returns
// 'application' (contains \\) — the correct answer, since PowerShell resolves
// this as a file path. After stripping it becomes 'Get-Process' which
// classifies as 'cmdlet' — wrong, and allowlist checks would trust it.
if (/[\u0080-\uFFFF]/.test(rawName)) {
  nameType = 'application'
} else {
  nameType = classifyCommandName(rawName)
}
name = stripModulePrefix(rawName)
```

**Flow:** first command element → prefer `.value` ONLY for string-literal element types (a numeric `ConstantExpressionAst` from `& 1` emits an integer `.value` that would crash `stripModulePrefix`) → strip surrounding quotes from the raw name at the SOURCE so every downstream reader (deny rules, `GIT_SAFETY_WRITE_CMDLETS`, `resolveToCanonical`) sees the bare name (`& 'Invoke-Expression'` yields `Invoke-Expression`) → non-ASCII name forces `'application'` → else classify: `Verb-Noun` regex ⇒ cmdlet, contains `.`/`\`/`/` ⇒ application, else unknown → `stripModulePrefix` refuses drive-letter (`C:\`), UNC (`\\`), and relative (`.\`, `..\`) forms.
**Invariant:** `nameType` is the ALLOWLIST gate (auto-allow paths require `!== 'application'`; six enforcement sites exist across the permission engine) while the stripped name feeds DENY matching, where over-match is fail-safe (`Module\Remove-Item` deny still hits plain `Remove-Item`). The non-ASCII force-application rule is defense-in-depth against .NET `OrdinalIgnoreCase` folding U+017F/U+0131 (`ſtart-proceſſ` → Start-Process) which JS `.toLowerCase()` cannot see (finding #31; verified NOT resolving on pwsh 7.x, retained anyway). `COMMON_ALIASES` uses `Object.create(null)` so attacker-controlled names like `constructor` return undefined, and ambiguous aliases (`sc`, `sort`, `curl`, `wget`) are DELIBERATELY unmapped because alias resolution precedes safety checks — mapping `sort → Sort-Object` would auto-allow `sort.exe /O C:\evil.txt`. `resolveToCanonical` strips PATHEXT (`.exe/.cmd/.bat/.com`, never `.ps1`) only on PATH-FREE names, so `scripts\git.exe` cannot canonicalize to `git` and dodge git-safety guards.
**Probe:** `grep -nF "nameType MUST be computed from the raw name" src/utils/powershell/parser.ts` and `grep -nF "Object.create(null)" src/utils/powershell/parser.ts` and `grep -cF "WINDOWS_PATHEXT" src/tools/PowerShellTool/readOnlyValidation.ts` → `2` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "transformCommandAst nameType stripModulePrefix classifyCommandName", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-copy discipline (raw-derived classifier + stripped matcher) and the null-prototype alias table with its omission list. Adapt the specific Verb-Noun regex to your host's command grammar. Omit the Windows-verification anecdotes. Coverage caveat: no upstream tests on this host; graph confirms `transformCommandAst` :830-935 and `stripModulePrefix` :814-826 line-exact (BM25 rank#1).
