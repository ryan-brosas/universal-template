<!-- capsule-v2 -->
# Formatting and layout — does code match C# mechanical conventions?

**Source:** C# coding conventions §Style guidelines, §Layout. **Question:** Will EditorConfig/dotnet format and layout rules pass on changed files?

## Layout seam
**Path/Symbol:** `*.cs` source files.
**Signature:** 4-space indent; Allman braces; file-scoped namespace when single namespace.
**Data Shape:** one statement and one declaration per line.

### Decisive pattern
```csharp
using System.Collections.Generic;

namespace Billing.Invoices;

public sealed class InvoiceService
{
    private readonly IInvoiceRepository _repository;

    public InvoiceService(IInvoiceRepository repository)
    {
        _repository = repository;
    }

    public Invoice? Find(InvoiceId id)
    {
        return _repository.Find(id);
    }
}
```

**Flow:** usings outside namespace → file-scoped `namespace` when one namespace → Allman braces → blank line between members.
**Invariant:** tabs never used; `using` directives inside namespace block fail review unless `global::` justified.
**Probe:** `.editorconfig` / `dotnet format` verification exit 0; grep shows no `\t` indent.

## Brace and wrap seam
```csharp
if ((startX > endX) && (startX > previousX))
{
    TakeAction();
}

var query = from customer in customers
            where customer.City == "Seattle"
            select customer.Name;
```

**Flow:** opening `{` on new line aligned with control → wrap long conditions before binary operators → LINQ clauses align under `from`.
**Invariant:** K&R same-line `{` when project Allman profile is configured fails review.
**Probe:** IDE formatting profile matches repo `.editorconfig`; sample file formats clean.

## Comment seam
```csharp
/// <summary>
/// Finds an invoice by identifier.
/// </summary>
public Invoice? Find(InvoiceId id) { /* ... */ }

// The following declaration creates a query. It does not run the query.
var seattleCustomers = from customer in customers
                       where customer.City == "Seattle"
                       select customer.Name;
```

**Flow:** XML docs on public members → `//` comments on own line, capitalized, period-terminated.
**Invariant:** public member without XML summary fails review on library/application API.
**Probe:** CS1591 (missing XML comment) configured as warning/error for public API projects.

## Verdict
Adopt 4-space Allman layout, file-scoped namespaces, usings outside namespace. Learning note: `csharp-style-learning-note.md`.
