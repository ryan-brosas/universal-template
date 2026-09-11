<!-- capsule-v2 -->
# Framework naming — does public API follow FDG PascalCase discipline?

**Source:** FDG digest §Naming; MS naming guidelines. **Question:** Are namespaces, types, members, and parameters named for discoverability across CLR languages?

## Naming seam
**Path/Symbol:** public/protected API in .NET assemblies (any language).
**Signature:** PascalCase types/members; camelCase parameters; standard affixes.
**Data Shape:** scenario namespaces; CLR-neutral type names in signatures.

### Decisive pattern
```csharp
namespace Contoso.Billing.Invoices;

public interface IInvoiceRepository
{
    Invoice GetInvoice(int invoiceId);
}

public sealed class InvoiceRepository : IInvoiceRepository
{
    public Invoice GetInvoice(int invoiceId) { /* ... */ }
}
```

**Flow:** apply PascalCase to all public identifiers except parameters → camelCase parameters and descriptive generic names (`TSession`) with `T` when single type param → prefix interfaces with `I`; suffix `Exception`, `EventArgs`, `EventHandler`, `Attribute`, `Collection`, `Dictionary` only on matching types → name types/properties with nouns; methods/events with verbs; events use present/past tense (`Closing`/`Closed`), not `Before`/`After` prefixes → use scenario-based namespaces `Company.Product.Feature`; not org-chart hierarchy → prefer CLR names in API (`Int64`, `Single`) over language aliases → avoid Hungarian notation, underscores, hyphens, contractions, and non-standard acronyms → use well-known acronyms sparingly with proper casing (`Html`, `IO`) → plural noun enum names for `[Flags]` enums, singular otherwise.
**Invariant:** public `strCustomerId`, org-only namespace tree, or `BeforeSave` event naming fails FDG naming review.
**Probe:** Roslyn/StyleCop naming rules; manual suffix/prefix checklist on new public types.

## Discoverability seam
**Flow:** reserve the first name developers will type in a feature area for the aggregate entry type, not an abstract base.
**Invariant:** scenario entry type buried under `Base*`/`Abstract*` name fails discoverability review.
**Probe:** sample consumer code uses intended entry type name first.

## Verdict
FDG PascalCase/camelCase, standard affixes, scenario namespaces, CLR-neutral names. Learning note: `dotnet-style-learning-note.md`.
