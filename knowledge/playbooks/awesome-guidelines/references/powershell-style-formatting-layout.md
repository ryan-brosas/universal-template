<!-- capsule-v2 -->
# Formatting and layout — does OTBS + CmdletBinding match PoshCode style?

**Source:** PoshCode Style Guide §Code Layout and Formatting. **Question:** Are braces, indent, blocks, and line length consistent for diff-friendly PowerShell?

## Layout seam
**Path/Symbol:** `.ps1`, `.psm1`, advanced functions.
**Signature:** OTBS braces; 4-space indent; ≤115 columns; `[CmdletBinding()]`.
**Data Shape:** param → begin → process → end execution order.

### Decisive pattern
```powershell
function Get-ProjectName {
    [CmdletBinding()]
    param (
        [Parameter(ValueFromPipeline = $true)]
        [string]$Path
    )

    process {
        Split-Path -Path $Path -Leaf
    }
}
```

**Flow:** use One True Brace Style — opening `{` at end of statement line, closing `}` starts its own line → indent 4 spaces per level (tabs configured as spaces) → limit lines to ~115 characters; prefer splatting and paren/brace continuation over backtick → start scripts/functions with `[CmdletBinding()]` and consider pipeline input → write blocks in execution order: `param`, `begin`, `process`, `end` → surround function definitions with two blank lines → no trailing whitespace; avoid semicolon line terminators → space around operators and parameters; exceptions for switch colon syntax and unary operators → lowercase language keywords; UPPERCASE comment-based help keywords inside help blocks.
**Invariant:** missing `[CmdletBinding()]`, K&R closing brace on same line as statement body, or backtick continuation where splatting suffices fails layout review.
**Probe:** PSScriptAnalyzer/Invoke-Formatter; OTBS visual scan; line-length spot check.

## Hashtable seam
**Flow:** one key per line in multiline hashtables; align inline comments with two+ spaces when used.
**Invariant:** semicolon-terminated hashtable entries on separate lines fail style consistency review.
**Probe:** multiline `@{}` formatting check.

## Verdict
OTBS, four-space indent, CmdletBinding-first, ordered blocks, splat-over-backtick. Learning note: `powershell-style-learning-note.md`.
