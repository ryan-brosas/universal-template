<!-- capsule-v2 -->
# Naming and types — does PascalCase public API avoid My-shadow and Hungarian drift?

**Source:** MS naming conventions + coding conventions; Framework Design Guidelines; Cory Smith §Naming. **Question:** Can readers infer member role from PascalCase/camelCase without legacy type prefixes?

## Naming seam
**Path/Symbol:** classes, interfaces, methods, fields, parameters.
**Signature:** PascalCase types/members; camelCase locals/params; optional `m_` private fields.
**Data Shape:** verb methods; noun types; `I` interfaces; no `My`/`my` in names.

### Decisive pattern
```vb
Public Interface IOrderRepository
    Function FindById(orderId As Integer) As Order
End Interface

Public Class SqlOrderRepository
    Implements IOrderRepository

    Private m_connectionString As String

    Public Event OrderSaved As EventHandler(Of OrderEventArgs)

    Public Function FindById(orderId As Integer) As Order Implements IOrderRepository.FindById
        Return LoadOrder(orderId)
    End Function

    Private Function LoadOrder(orderId As Integer) As Order
        Dim sql As String = "SELECT ..."
        Return ExecuteQuery(sql)
    End Function
End Class
```

**Flow:** capitalize each word in identifiers (`FindLastRecord`) → start methods with verbs (`CloseDialog`); classes/structures/properties with nouns (`EmployeeName`) → prefix interfaces with `I` without underscores (`IComponent`) → suffix event arg types with `EventArgs`; event handlers with event noun + handler pattern → use camelCase for parameters and local variables → use PascalCase for public properties, methods, events, classes → optional `m_` prefix on private instance fields when backing properties (VB case-insensitivity collision guard per Cory Smith) → do not embed `My` or `my` in names (conflicts with `My` objects) → avoid Hungarian type prefixes on new .NET code (`strX`, `iCount` from Wikibooks legacy) → avoid shadowing outer-scope names; keep names ≤32 chars when practical → do not use type suffix characters (`$`, `%`, `#`).
**Invariant:** lowercase public type name, `My`-prefixed field, or Wikibooks-style `g`/`m`/`i` prefix on new VB.NET fails naming review.
**Probe:** public API PascalCase audit; Hungarian-prefix grep on non-legacy paths.

## Type/file seam
**Flow:** one public type per file named after the public class; directories mirror namespace.
**Invariant:** multiple public classes in one `.vb` without split plan fails file review.
**Probe:** filename ↔ public type match; folder/namespace alignment.

## Verdict
Framework-aligned PascalCase/camelCase, optional `m_` fields, no My/Hungarian on new code. Learning note: `vb-style-learning-note.md`.
