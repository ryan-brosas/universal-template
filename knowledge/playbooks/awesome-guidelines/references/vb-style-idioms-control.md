<!-- capsule-v2 -->
# Idioms and control — are Strict options and modern VB patterns enforced?

**Source:** MS coding conventions §Language Guidelines; Cory Smith §Option Strict/VB.NET Way. **Question:** Does the file use Try/Catch, interpolation, and LINQ/event idioms instead of legacy VB6 patterns?

## Options seam
**Path/Symbol:** top of every hand-written `.vb` file.
**Signature:** `Option Strict On`; `Option Explicit On`; comment if either must be Off.
**Data Shape:** compile-time type safety before idioms review.

### Decisive pattern
```vb
Option Strict On
Option Explicit On

Imports System.Linq

Public Module StringFilters

    Public Function ActiveCustomerNames(customers As IEnumerable(Of Customer)) As List(Of String)
        Dim results = From cust In customers
                      Where cust.IsActive
                      Order By cust.LastName
                      Select cust.DisplayName
        Return results.ToList()
    End Function

End Module
```

**Flow:** place `Option Strict On` and `Option Explicit On` at file top (or document why Off) → use `$"..."` string interpolation for short concatenation; `StringBuilder` in tight loops → `Try`/`Catch`/`Finally` and `Using` for disposal; never `On Error Goto` → prefer `target IsNot Nothing` over `Not target Is Nothing` → `Dim list As New List(Of T)` short instantiation; object initializers with `With { .Prop = value }` → array syntax `Dim letters As String() = {"a","b"}` with designator on type → call `Shared` members through type name → events: prefer `Handles`; relaxed handlers when args unused; `AddressOf` without explicit delegate `New` → LINQ: meaningful query variable names; name anonymous-type elements; `Where` before `Order By`; explicit `Join` not hidden in `Where` → use `Module` for shared-only helpers; not a class of only Shared methods → avoid `Microsoft.VisualBasic.Compatibility` APIs.
**Invariant:** Option Strict Off on new code without waiver, `On Error`, or Compatibility namespace use fails idioms review.
**Probe:** file-header option grep; `On Error` / Compatibility namespace scan.

## Control seam
**Flow:** `With` for repeated calls on one object; `Integer` over unsigned unless required.
**Invariant:** repeated `obj.Prop =` chains without `With` where readability suffers fails minor idioms review.
**Probe:** With-block opportunity spot check on changed methods.

## Verdict
Strict options, Try/Catch, IsNot, modern strings/arrays/events/LINQ/Module patterns. Learning note: `vb-style-learning-note.md`.
