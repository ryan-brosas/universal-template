<!-- capsule-v2 -->
# Naming and commands — are Verb-Noun tools spelled out for readers?

**Source:** PoshCode Style Guide §Naming; §Capitalization. **Question:** Do shared scripts use full cmdlet names, PascalCase, and portable paths?

## Naming seam
**Path/Symbol:** functions, parameters, variables in modules and shared scripts.
**Signature:** approved `Verb-Noun`; PascalCase public identifiers; full `-Parameter` names.
**Data Shape:** `$PSScriptRoot`-anchored paths; `$Script:` scope for shared state.

### Decisive pattern
```powershell
function Get-RepoReadme {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [string]$RepositoryRoot
    )

    $readmePath = Join-Path -Path $RepositoryRoot -ChildPath 'README.md'
    Get-Content -Path $readmePath
}
```

**Flow:** name advanced functions with approved `Verb-Noun` (`Get-Verb` list); PascalCase within verb and noun → PascalCase all public identifiers including parameters → use full cmdlet names in shared code (`Get-Process`, not `gps`) → use full parameter names (`-Name`, not bare positional) → build paths from `$PSScriptRoot` with `Join-Path`; avoid `.`, `..`, and `~` in portable scripts — especially for .NET APIs where `[Environment]::CurrentDirectory` differs from `$PWD` → optional camelCase for private function variables; use `$Script:`/`$Global:` for shared scope → two-letter acronyms both caps in Pascal names (`PSBoundParameters`); do not extend to compound acronyms (`AzureRmVM` pattern).
**Invariant:** alias cmdlets, bare positional-only calls, or `.\file.txt` without `$PSScriptRoot` in shared modules fails naming/portability review.
**Probe:** alias grep on exported scripts; path construction audit.

## Capitalization seam
**Flow:** lowercase operators (`-eq`, `-match`); help block keywords UPPERCASE (`.SYNOPSIS`).
**Invariant:** uppercase `-EQ` or lowercase public function name fails capitalization review.
**Probe:** public identifier PascalCase scan.

## Verdict
Verb-Noun, PascalCase public surface, explicit parameters, `$PSScriptRoot` paths. Learning note: `powershell-style-learning-note.md`.
