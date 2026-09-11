<!-- capsule-v2 -->
# Exceptions, events, and disposal — do failures and lifetimes follow FDG patterns?

**Source:** FDG digest exception/event/dispose rules. **Question:** Are errors, events, and native resources expressed with BCL-standard patterns?

## Failure seam
**Path/Symbol:** public methods and resource-holding types.
**Signature:** specific exceptions; `EventHandler<TEventArgs>`; `IDisposable` for native resources.
**Data Shape:** consistent overload chains; no error codes.

### Decisive pattern
```csharp
public event EventHandler<InvoicePostedEventArgs>? InvoicePosted;

public void PostInvoice(Invoice invoice)
{
    ArgumentNullException.ThrowIfNull(invoice);
    if (invoice.IsPosted)
        throw new InvalidOperationException("Invoice already posted.");
    // ...
    InvoicePosted?.Invoke(this, new InvoicePostedEventArgs(invoice.Id));
}

public sealed class NativeHandle : IDisposable
{
    public void Dispose() { /* release native */ }
}
```

**Flow:** report failures with exceptions, never error codes → throw specific BCL exceptions when possible (`ArgumentNullException`, `ArgumentOutOfRangeException`, `InvalidOperationException`) → do not throw `Exception` or `SystemException` → avoid catching base `Exception` without rethrow/filter strategy → write clear actionable exception messages → use `EventHandler<TEventArgs>` instead of custom delegate types for events → prefer event-based APIs over exposed delegate properties → implement `IDisposable` on types holding native resources; avoid finalizers unless necessary → keep related overloads with consistent parameter order; put core logic in widest overload → avoid `out`/`ref` in public APIs when alternatives exist → prefer constructors over factories unless factory adds clear value.
**Invariant:** bare `throw new Exception`, public `out` parameters for optional data, or native handle type without `IDisposable` fails failure/lifetime review.
**Probe:** exception type grep; IDisposable on native wrappers; overload consistency check.

## Event naming seam
**Flow:** present-tense before event (`Closing`); past-tense after (`Closed`).
**Invariant:** `BeforeClose`/`AfterClose` event pair naming fails FDG event review.
**Probe:** new event name suffix/prefix scan.

## Verdict
Specific exceptions, standard event pattern, IDisposable for native resources, consistent overloads. Learning note: `dotnet-style-learning-note.md`.
