---
title: powershell-scripting-practices
summary: Use when authoring or reviewing PowerShell, PoshCode OTBS layout, Verb-Noun CmdletBinding functions, pipeline tool patterns, try/catch with -ErrorAction Stop, PSCredential security, and PSScriptAnalyzer in CI.
kind: playbook
---

# PowerShell Scripting Practices

Application skill for PoshCode PowerShellPracticeAndStyle. For bash glue, use `shell-scripting-practices`. For.NET library API naming, use `dotnet-coding-practices`.

## Core Principle

PowerShell quality is **advanced functions emitting pipeline objects with explicit, trappable errors**, not Write-Host scripts with alias cmdlets.

## When to Use / NOT

- `.ps1` controllers, `.psm1` modules, advanced functions, Azure/automation scripts.
- Reviewing Verb-Noun tools, error handling, credential handling, formatting rules.

**NOT when:**

- Bash/sh only environments, `shell-scripting-practices`.
- C#/VB syntax, language practice skills.
- Generated Pester stub files, validate generators.

## Workflow

1. **Formatting**, OTBS, blocks, splatting.
2. **Naming**, Verb-Noun, full cmdlets, paths.
3. **Functions/tools**, process output, raw objects.
4. **Errors/security**, Stop, try/catch, PSCredential.
5. **Verify**, PSScriptAnalyzer + `Invoke-Formatter` on changed scripts.

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
