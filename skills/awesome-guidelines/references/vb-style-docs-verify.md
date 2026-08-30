<!-- capsule-v2 -->
# Documentation and verification — is public API documented and build-clean?

**Source:** Cory Smith §Documentation/File Organization; MS coding conventions. **Question:** Do public members carry XML docs and do gates pass after changes?

## Documentation seam
**Path/Symbol:** public classes, methods, properties.
**Signature:** `'''` XML summaries; `<param>`/`<returns>` on exports.
**Data Shape:** copyright/header optional; `<devdoc>` for internal notes (Cory Smith).

### Decisive pattern
```vb
''' <summary>Loads an order by identifier.</summary>
''' <param name="orderId">Primary key of the order.</param>
''' <returns>The matching order record.</returns>
Public Function FindById(orderId As Integer) As Order
    If orderId <= 0 Then
        Throw New ArgumentOutOfRangeException(NameOf(orderId))
    End If
    Return LoadOrder(orderId)
End Function
```

**Flow:** add `'''` XML documentation to all public types and members → document parameters, returns, and side effects on value-moving methods → use `<devdoc>` for internal maintainer notes when needed → group class members by visibility (Public → Protected → Friend → Private) and alphabetize within section when practical (Cory Smith) → keep one public type per file named after the type; folder path mirrors namespace → for legacy VB6 maintenance only: Wikibooks Hungarian prefixes may remain in untouched blocks — do not extend into new .NET code.
**Invariant:** new public method without XML summary or multiple public types per file fails docs review.
**Probe:** public API XML coverage diff; file/type count check.

## Verify seam
**Flow:** `dotnet build` on changed projects; `dotnet format --verify-no-changes` when configured; unit tests on touched behavior.
**Invariant:** compile error or formatter drift on PR diff fails verify gate.
**Probe:** build/test CI output; format check on changed `.vb`.

## Verdict
XML-documented public surface, organized files, dotnet build/format/test on changes. Learning note: `vb-style-learning-note.md`.
