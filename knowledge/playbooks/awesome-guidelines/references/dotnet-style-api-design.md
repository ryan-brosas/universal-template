<!-- capsule-v2 -->
# API design — are top scenarios one-liners via aggregate components?

**Source:** FDG digest §General Design Principles/Guidelines. **Question:** Can main scenarios be written with minimal ceremony using intuitive entry types?

## Design seam
**Path/Symbol:** reusable .NET libraries and shared components.
**Signature:** scenario-first samples; aggregate component per feature; create-set-call.
**Data Shape:** properties over fields; typed collections in public surface.

### Decisive pattern
```csharp
var log = new EventLog();
log.Source = "BillingService";
log.WriteEntry("Invoice posted.");

IReadOnlyCollection<Invoice> open = repository.GetOpenInvoices(customerId);
```

**Flow:** start design by writing end-user scenario code for each feature → pick intuitive aggregate component names from those samples → enable create-set-call: default ctor, set properties, call simple methods → keep main scenarios to a few lines; redesign if samples grow long → model physical concepts (`File`, `Directory`) over low-level tasks when choosing aggregate names → return most derived types, accept least derived inputs → expose collections (`Collection<T>`, `ReadOnlyCollection<T>`, `KeyedCollection<,>`) not arrays/`List<T>`/`Dictionary<,>` in public API → use properties for logical state; use methods for conversions, expensive ops, side effects, unstable reads, or array returns (return copies) → properties settable in any order without hidden cross-property state → prefer classes over interfaces; ship each public interface with concrete implementation and at least one consuming API → mark `[CLSCompliant(true)]` on libraries → apply `[Flags]` to flag enums.
**Invariant:** simple scenario requiring many object types, public fields, or raw arrays in API fails API design review.
**Probe:** scenario sample code review; public surface collection/array audit.

## Extensibility seam
**Flow:** avoid sealing and virtual members unless extension point is intentional; avoid public nested types.
**Invariant:** sealed base library type without documented closure reason fails extensibility review.
**Probe:** `sealed`/`virtual` audit on new public types.

## Verdict
Scenario-driven aggregate APIs, create-set-call ergonomics, collection-based public surface. Learning note: `dotnet-style-learning-note.md`.
