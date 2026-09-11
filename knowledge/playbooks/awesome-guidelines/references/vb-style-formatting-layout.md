<!-- capsule-v2 -->
# Formatting and layout — does Pretty Listing leave the file unchanged?

**Source:** MS Visual Basic coding conventions §Layout; Cory Smith §Tabs/Block. **Question:** Are statements, spacing, and comments readable at four spaces without line-separator tricks?

## Layout seam
**Path/Symbol:** `.vb` source files.
**Signature:** 4-space indent; one statement per line; blank line between members.
**Data Shape:** implicit line continuation; left-aligned declaration lists.

### Decisive pattern
```vb
Option Strict On
Option Explicit On

Public Class OrderProcessor

    Public Sub ProcessOrder(orderId As Integer)
        If orderId <= 0 Then
            Throw New ArgumentOutOfRangeException(NameOf(orderId))
        End If

        Dim label As String = $"Order-{orderId}"
        SaveLabel(label)
    End Sub

    Private Sub SaveLabel(label As String)
        ' Persist the generated label.
    End Sub

End Class
```

**Flow:** indent with 4 spaces (tabs inserted as spaces) — run Visual Studio **Pretty Listing** so reformatted code matches repo style → one statement per line; never use `:` line separator → prefer implicit line continuation over `_` when the language allows → one declaration per line; left-align items in split declaration lists → add at least one blank line between method and property definitions → put comments on their own line; start with uppercase; end with period; one space after `'` → avoid asterisk comment boxes → use full `If`/`Then`/`End If` blocks for multiline bodies; avoid empty `Else` branches without comment.
**Invariant:** multi-statement lines, missing blank lines between members, or trailing inline comment walls fail layout review.
**Probe:** VS Pretty Listing / `dotnet format`; `grep ':'` for statement separators; member spacing scan.

## Spacing seam
**Flow:** single space after comma in arg lists; no space between function name and `(`; space around comparison operators.
**Invariant:** `CreateWorld( arg )` or `If (x=y)` spacing fails Cory Smith spacing review.
**Probe:** argument/comparison spacing spot check.

## Verdict
Four-space, one-statement-per-line, blank-line member rhythm, `' Comment.` style. Learning note: `vb-style-learning-note.md`.
