# PowerShell style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `powershell-style-*.md` capsules, `powershell-scripting-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [PoshCode PowerShellPracticeAndStyle](https://github.com/PoshCode/PowerShellPracticeAndStyle) — Style Guide: Code Layout, Naming, Function Structure, Documentation (primary) | OTBS braces; 4-space indent; 115 cols; `[CmdletBinding()]`; param/process/end order; PascalCase public IDs; Verb-Noun; full cmdlet/param names; comment-based help inside functions |
| Same repo — Best Practices: Building Reusable Tools, Error Handling, Output, Security (primary) | Tool vs controller; pipeline objects; `-ErrorAction Stop`; try/catch transactions; avoid `$?`; PSCredential; Write-Verbose/Debug not Write-Host for data |
| [PSScriptAnalyzer](https://github.com/PowerShell/PSScriptAnalyzer) (secondary) | Invoke-Formatter; automated rule enforcement in CI |

**Scope:** PowerShell 5+ / 7+ scripts, modules, advanced functions. Bash-only glue: use `shell-scripting-practices`. .NET public API naming: use `dotnet-coding-practices`.

## Mental model

PowerShell quality is **advanced functions + pipeline objects + explicit errors**:

1. **Formatting** — OTBS, 4 spaces, splatting over backtick, `[CmdletBinding()]`, ordered blocks.
2. **Naming/commands** — Verb-Noun, full cmdlets/parameters, PascalCase, `$PSScriptRoot` paths.
3. **Functions/tools** — process-block output, parameter validation attributes, raw tool output vs formatted controllers.
4. **Errors/security** — `-ErrorAction Stop`, try/catch scope, PSCredential, PSScriptAnalyzer.

## Decision tables

### Layout & formatting

| Topic | Rule |
|---|---|
| Braces | OTBS — opening `{` end of line; closing at line start |
| Indent | 4 spaces (not tabs) |
| Line length | ≤115 chars; splatting/paren continuation over backtick |
| Blocks | `[CmdletBinding()]`; param → begin → process → end order |
| Spacing | space around operators; no trailing whitespace |
| Blank lines | 2 between functions; EOF newline |
| Semicolons | avoid as line terminators |
| Keywords | lowercase (`foreach`, `-eq`); help keywords UPPERCASE |

### Naming & commands

| Entity | Convention |
|---|---|
| Public identifiers | PascalCase (including parameters) |
| Functions/cmdlets | approved `Verb-Noun` (`Get-Verb`) |
| Commands | full names (`Get-Process` not `gps`) |
| Parameters | full names (`-Name` not positional-only) |
| Paths | `$PSScriptRoot` + `Join-Path`; avoid `.`/`..` and `~` in shared scripts |
| Scope vars | `$Script:` / `$Global:` when shared |
| Private vars | optional camelCase |

### Advanced functions & tools

| Case | Rule |
|---|---|
| Binding | always `[CmdletBinding()]` |
| Pipeline | output in `process {}`; avoid `return` in advanced functions |
| OutputType | `[OutputType()]` when returning objects |
| Parameter sets | `DefaultParameterSetName` when using sets |
| Validation | prefer parameter attributes over manual body checks |
| Tool vs controller | tools: parameters in, objects out; controllers: orchestrate, may format |
| Tool output | raw data; formatting in controller or `.format.ps1xml` |
| Write-Host | only Show/Format/interactive prompts — not script output |
| Streams | Write-Progress, Write-Verbose, Write-Debug appropriately |
| Single type | one object kind per command output |

### Errors & security

| Case | Rule |
|---|---|
| Cmdlets | `-ErrorAction Stop` for trappable errors |
| Native/other | `$ErrorActionPreference = 'Stop'` around risky block |
| Pattern | whole transaction in try/catch, not flag variables |
| Avoid | `$?` for error details; null-test as error proxy when exception possible |
| catch | copy `$_` / `$Error[0]` immediately |
| Credentials | `[PSCredential]` + `[Credential()]` attribute; no plain-text passwords |
| Secrets | SecureString; Export-CliXml for saved creds |
| Verify | PSScriptAnalyzer / Invoke-Formatter in CI |

## Anti-patterns

- Script/function without `[CmdletBinding()]`
- K&R or Allman inconsistency (mixed brace styles)
- Backtick line continuation when paren/splat works
- Positional-only parameter use in shared scripts
- Alias cmdlets (`gps`, `gci`) in shared code
- Relative paths with .NET APIs without `$PSScriptRoot`
- `~` for home in portable scripts
- `return` in advanced function `end` block for pipeline output
- Output in `begin`/`end` instead of `process` for pipeline functions
- Write-Host for data output
- Mixed object types to pipeline without `Out-Default` separation
- Reinventing built-in commands (Ping vs Test-Connection)
- Plain string passwords or `Get-Credential` hidden inside function
- Flag-variable error handling (`$continue`)
- `$?` as error probe
- Missing comment-based help on exported functions
- Trailing whitespace; semicolon line terminators
- Whitespace-only reformat mixed with logic commits

## Skill trace

| Artifact | Role |
|---|---|
| `powershell-style-formatting-layout.md` | OTBS, indent, CmdletBinding blocks |
| `powershell-style-naming-commands.md` | Verb-Noun, full names, paths |
| `powershell-style-functions-tools.md` | process output, tools, streams |
| `powershell-style-errors-security.md` | try/catch, PSCredential, analyzer |
| `powershell-scripting-practices/SKILL.md` | PSScriptAnalyzer in CI |
