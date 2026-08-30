---
name: powershell-scripting-practices
description: "Use when authoring or reviewing PowerShell — PoshCode OTBS layout, Verb-Noun CmdletBinding functions, pipeline tool patterns, try/catch with -ErrorAction Stop, PSCredential security, and PSScriptAnalyzer in CI."
disable-model-invocation: true
---

# PowerShell Scripting Practices

Application skill for PoshCode PowerShellPracticeAndStyle (archived `awesome-guidelines` capsules). For bash glue, use `shell-scripting-practices`. For .NET library API naming, use `dotnet-coding-practices`.

## Core Principle

PowerShell quality is **advanced functions emitting pipeline objects with explicit, trappable errors** — not Write-Host scripts with alias cmdlets.

## When to Use / NOT

- `.ps1` controllers, `.psm1` modules, advanced functions, Azure/automation scripts.
- Reviewing Verb-Noun tools, error handling, credential handling, formatting rules.

**NOT when:**

- Bash/sh only environments — `shell-scripting-practices`.
- C#/VB syntax — language practice skills.
- Generated Pester stub files — validate generators.

## Workflow

1. **Formatting** — OTBS, blocks, splatting (`powershell-style-formatting-layout.md`).
2. **Naming** — Verb-Noun, full cmdlets, paths (`powershell-style-naming-commands.md`).
3. **Functions/tools** — process output, raw objects (`powershell-style-functions-tools.md`).
4. **Errors/security** — Stop, try/catch, PSCredential (`powershell-style-errors-security.md`).
5. **Verify** — PSScriptAnalyzer + `Invoke-Formatter` on changed scripts.

## Red Flags

- Missing `[CmdletBinding()]`
- Mixed/inconsistent brace style
- Backtick continuation where splatting/parens work
- Alias cmdlets or positional-only calls in shared code
- Relative paths/`~` without `$PSScriptRoot` discipline
- `return` in advanced function for pipeline emission
- Output from `begin`/`end` instead of `process` for pipeline input
- Write-Host for data output (non-Show/Format)
- Mixed pipeline object types without separation
- Custom ping/file helpers ignoring built-in cmdlets
- Plain-text password parameters
- `Get-Credential` inside reusable function
- `$continue` flag error handling
- `$?` used as error detail probe
- Null-test instead of exception on failing cmdlet
- Exported function missing comment-based help
- Trailing whitespace or semicolon terminators
- PSScriptAnalyzer findings ignored without rationale

## Verification

- `Invoke-ScriptAnalyzer` (PSScriptAnalyzer) on changed `.ps1`/`.psm1`
- `Invoke-Formatter` / project formatter check when configured
- Pipeline test for `ValueFromPipeline` functions
- Failure-path test with `-ErrorAction Stop` behavior
- Capsule checklist on tool vs controller split

## Skill Result Contract

```xml
<skill_result>
  <skill>powershell-scripting-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>ps1/psm1 diff, PSScriptAnalyzer output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>non-terminating errors, plain credentials, or Write-Host output</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/powershell-style-learning-note.md`
- `awesome-guidelines/references/powershell-style-formatting-layout.md`
- `awesome-guidelines/references/powershell-style-naming-commands.md`
- `awesome-guidelines/references/powershell-style-functions-tools.md`
- `awesome-guidelines/references/powershell-style-errors-security.md`
