<!-- capsule-v2 -->
# Naming and types — do identifiers follow Framework Design rules?

**Source:** .NET naming/capitalization guidelines; names of classes/structs/interfaces. **Question:** Are public API names PascalCase-clear and suffix-correct?

## Capitalization seam
**Path/Symbol:** public/protected types and members.
**Signature:** PascalCase types/members; camelCase parameters only.
**Data Shape:** no underscores; no Hungarian notation.

### Decisive pattern
```csharp
namespace System.Security.Cryptography;

public interface IInvoiceRepository
{
    Invoice? FindById(InvoiceId invoiceId);
}

public sealed class InvoiceNotFoundException : Exception
{
    public InvoiceNotFoundException(InvoiceId id)
        : base($"Invoice not found: {id}") { }
}

public enum InvoiceStatus
{
    Draft,
    Posted,
}
```

**Flow:** namespace Pascal segments → interface `I` prefix → types as nouns → exceptions `…Exception` → enum singular type name, Pascal values without prefix.
**Invariant:** `invoice_id`, `strName`, `StatusEnum`, `IFooInterface` fail review.
**Probe:** naming analyzers (IDE0001 series) / custom rules on public API diff.

## Compound words and acronyms seam
```csharp
public class HttpClientFactory { }
public IOStream OpenStream() { /* ... */ }

public void SignIn(string userName) { }
public void LogOff() { }
```

**Flow:** treat closed compounds as single words (`FileName`, `Endpoint`, `SignIn`) → two-letter acronyms both caps (`IOStream`); longer acronyms capitalize first letter only (`HttpClient`).
**Invariant:** `EndPoint`, `UserName` vs `Username` inconsistency with guideline table fails review.
**Probe:** manual scan against [compound word table](https://learn.microsoft.com/en-us/dotnet/standard/design-guidelines/capitalization-conventions).

## Generics seam
```csharp
public interface ISessionChannel<TSession> where TSession : ISession
{
    TSession Session { get; }
}

public delegate bool Predicate<T>(T item);
```

**Flow:** single-letter `T` when self-explanatory → descriptive type params prefixed with `T` (`TSession`) → constraints may appear in name when helpful.
**Invariant:** generic parameter named `K` without domain meaning on multi-param type fails review.
**Probe:** public generic API readable without reading constraint clauses.

## Verdict
PascalCase surface, camelCase parameters, interface `I`, standard suffixes, compound-word discipline. Learning note: `csharp-style-learning-note.md`.
