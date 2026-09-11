<!-- capsule-v2 -->
# Errors and security — are failures trappable and secrets typed?

**Source:** PoshCode Best Practices §Error Handling, §Security. **Question:** Do cmdlets stop on error, transactions use try/catch, and credentials stay off plain strings?

## Error seam
**Path/Symbol:** cmdlets, native calls, credential parameters.
**Signature:** `-ErrorAction Stop`; try/catch transactions; `[PSCredential]` parameters.
**Data Shape:** copied `$_` in catch; SecureString for secrets.

### Decisive pattern
```powershell
function Set-RemoteShare {
    [CmdletBinding()]
    param (
        [Parameter(Mandatory = $true)]
        [System.Management.Automation.PSCredential]
        [System.Management.Automation.Credential()]
        $Credential,

        [Parameter(Mandatory = $true)]
        [string]$SharePath
    )

    process {
        try {
            New-SmbShare -Name 'Data' -Path $SharePath -Credential $Credential -ErrorAction Stop
            Write-Verbose "Share created at $SharePath"
        }
        catch {
            $err = $_
            Write-Error -Message $err.Exception.Message -ErrorId $err.FullyQualifiedErrorId
        }
    }
}
```

**Flow:** call cmdlets with `-ErrorAction Stop` when trapping errors → set `$ErrorActionPreference = 'Stop'` around non-cmdlet code that must terminate → put whole logical transaction inside try/catch instead of `$continue` flags → avoid `$?` for error diagnosis → avoid null-variable tests as error handling when terminating exceptions are available → copy `$_` or `$Error[0]` to a local variable immediately in catch → accept credentials as `[PSCredential]` with `[Credential()]` attribute; do not call `Get-Credential` inside reusable functions → never store passwords in plain strings; use SecureString and Export-CliXml for persisted creds on disk → decrypt secrets only at point of use; zero sensitive buffers when converting SecureString → run PSScriptAnalyzer (and Invoke-Formatter) in CI on changed scripts/modules.
**Invariant:** bare `$?` check after failure, plain-text password parameter, or cmdlet call without `-ErrorAction Stop` inside try scope fails error/security review.
**Probe:** PSScriptAnalyzer security/error rules; credential parameter attribute audit.

## Output vs error seam
**Flow:** use Write-Error/throw for failures; Write-Verbose for non-essential runtime detail.
**Invariant:** silent failure with only Write-Host message fails operability review.
**Probe:** failure-path test asserts error record or non-zero exit.

## Verdict
Stop-on-error, try/catch transactions, PSCredential parameters, analyzer-gated scripts. Learning note: `powershell-style-learning-note.md`.
