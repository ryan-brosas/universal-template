<!-- capsule-v2 -->
# Functions and tools — do advanced functions emit pipeline objects correctly?

**Source:** PoshCode Function Structure; Best Practices §Building Reusable Tools, §Output. **Question:** Are tools reusable (objects in/out) and controllers separate from formatting?

## Tool seam
**Path/Symbol:** advanced functions in modules; controller scripts.
**Signature:** `[CmdletBinding()]`; `process` output; `[OutputType()]`; parameter validation attributes.
**Data Shape:** raw objects from tools; formatted output only in controllers/Show/Format.

### Decisive pattern
```powershell
function Get-DiskBytes {
    [CmdletBinding()]
    [OutputType([psobject])]
    param (
        [Parameter(ValueFromPipeline = $true)]
        [ValidateNotNullOrEmpty()]
        [string]$ComputerName
    )

    process {
        Get-CimInstance -ClassName Win32_LogicalDisk -ComputerName $ComputerName |
            Select-Object DeviceID, @{ Name = 'SizeBytes'; Expression = { $_.Size } }
    }
}
```

**Flow:** classify code as reusable **tool** (function/module) vs **controller** script (one business process) → tools accept parameters and emit objects to pipeline; avoid unnecessary formatting → output from `process {}` for pipeline-bound functions; do not use `return` to emit in advanced functions → declare `[OutputType()]`; set `DefaultParameterSetName` when using parameter sets → prefer validation attributes (`ValidateSet`, `ValidateRange`, …) over manual param checks in body → tools return raw data (bytes, not gigabytes); controllers or `.format.ps1xml` views handle presentation → do not use `Write-Host` for script output except Show/Format verbs or interactive prompts → use Write-Progress, Write-Verbose, Write-Debug for status/diagnostics → emit one object kind per external command → wrap external CLIs in advanced functions when no native cmdlet exists → prefer built-in commands before reinventing (`Test-Connection` vs custom ping).
**Invariant:** pipeline function returning only from `end` with `return`, tool emitting formatted strings via Write-Host, or mixed types without separation fails tool review.
**Probe:** pipeline `ValueFromPipeline` test; OutputType attribute check; Write-Host grep on non-Show functions.

## Help seam
**Flow:** comment-based help inside function top; per-parameter comments above params in `param` block; include `.EXAMPLE`.
**Invariant:** exported function without comment-based help fails docs review.
**Probe:** `Get-Help` renders synopsis/parameters/examples.

## Verdict
CmdletBinding advanced functions, process-block pipeline output, raw tool data, controller formatting split. Learning note: `powershell-style-learning-note.md`.
