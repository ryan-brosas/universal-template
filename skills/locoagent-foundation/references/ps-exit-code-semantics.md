<!-- capsule-v2 -->
# PS exit-code semantics table — which Windows-native exit codes mean success, and why must the extractor be heuristic-only?

**Source:** LocoAgent MIT `main@c01bb3f8`; Codebase Memory `locoagent`. **Question:** How should a PowerShell runner interpret non-zero exits from robocopy/grep/findstr without mislabeling successes as errors?

## Bitfield + no-match semantics keyed on basename; cmdlets deliberately excluded
**Path/Symbol:** `src/tools/PowerShellTool/commandSemantics.ts`:`COMMAND_SEMANTICS` (:62-94 — grep/rg/findstr share GREP_SEMANTIC `isError: exitCode >= 2`; robocopy bitfield `isError: exitCode >= 8` with per-bit messages), `interpretCommandResult` (:130-142), `heuristicallyExtractBaseCommand` (:121-125).
**Signature:** `type CommandSemantic = (exitCode, stdout, stderr) => { isError: boolean; message?: string }`; `function interpretCommandResult(command: string, exitCode: number, stdout: string, stderr: string)`.
**Data Shape:** Map keys lowercase WITHOUT `.exe`; extractor strips `&`/`.` call operators, quotes, path segments.

### Decisive source
```ts
// robocopy.exe ... Exit codes are a BITFIELD — 0-7 are success, 8+ indicates at least one failure:
//   0 = no files copied (already in sync)   1 = files copied successfully
//   2 = extra files detected                4 = mismatched files detected
//   8 = some files could not be copied     16 = serious error
// This is the single most common "CI failed but nothing's wrong" Windows gotcha.
['robocopy', (exitCode) => ({ isError: exitCode >= 8, ... })],
```

**Flow:** split command heuristically on `;`/`|`, take the LAST segment (it owns the exit code) → strip call operators/quotes/paths/`.exe` → semantic lookup or DEFAULT (non-zero = error). Deliberate omissions documented: `diff`/`fc`/`find` are alias-ambiguous across PS editions (Compare-Object vs diff.exe semantics), so they keep the default rather than guess.
**Invariant:** This module is INFORMATIONAL ONLY — the comment pins it: "Do NOT depend on this for security; false negatives just fall back to default." Native cmdlets (Select-String/Compare-Object/Test-Path) exit 0 regardless and signal failure via `$?`, so they must never enter the map.
**Probe:** `grep -nF "isError: exitCode >= 8" src/tools/PowerShellTool/commandSemantics.ts` and `grep -nF "Do NOT depend on this for security" src/tools/PowerShellTool/commandSemantics.ts` (anchored at the locoagent repo root).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "interpretCommandResult COMMAND_SEMANTICS robocopy", limit: 10, fields: ["signature", "name", "file"] });
```
*(resolves PowerShellTool module symbols; bash twin is `bash-command-exit-semantics.md`)*

## Verdict
Adopt the last-segment extraction rule, the bitfield handling, and the ambiguity-omits policy. Adapt entries to your platform's binaries. Omit cross-shell comparisons beyond the pointer. Coverage caveat: probes deterministic; no upstream tests.
