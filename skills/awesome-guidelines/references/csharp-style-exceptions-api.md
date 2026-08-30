<!-- capsule-v2 -->
# Exceptions and API surface — are failures and public members explicit?

**Source:** C# coding conventions §try-catch, §Static members, §Security; Framework Design docs. **Question:** Are exceptions specific, statics qualified, and public API documented?

## Exception seam
**Path/Symbol:** methods with failure modes.
**Signature:** catch specific types; rethrow preserves stack; `using` for disposal.
**Data Shape:** no bare `catch (Exception)` without filter/strategy.

### Decisive pattern
```csharp
public static double ComputeDistance(double x1, double y1, double x2, double y2)
{
    try
    {
        return Math.Sqrt((x1 - x2) * (x1 - x2) + (y1 - y2) * (y1 - y2));
    }
    catch (ArithmeticException ex)
    {
        Logger.LogError(ex, "Overflow computing distance");
        throw;
    }
}

public void ProcessFont()
{
    using Font bodyStyle = new("Arial", 10.0f);
    byte charset = bodyStyle.GdiCharSet;
}
```

**Flow:** catch only handleable specific exceptions → log + `throw;` to preserve stack → replace try/finally+Dispose with `using`.
**Invariant:** empty catch, `catch (Exception)` without filter, and swallowing after catch fail review.
**Probe:** CA1031/CA2200 analyzer rules if enabled; tests cover exception paths.

## Static access seam
```csharp
var length = string.IsNullOrEmpty(value)
    ? 0
    : value.Length;

ExampleClass.Process(items);
```

**Flow:** call static members through declaring type name → never qualify base static via derived type name.
**Invariant:** `DerivedHelper.BaseMethod()` when static defined on base fails review.
**Probe:** grep static invocations use declaring type in diff.

## Delegates and LINQ API seam
```csharp
Action<string> log = message => Console.WriteLine(message);
Func<int, int, int> add = (x, y) => x + y;

var seattleCustomers =
    from customer in customers
    where customer.City == "Seattle"
    orderby customer.Name
    select customer;
```

**Flow:** prefer `Func<>`/`Action<>` over custom delegate types → meaningful LINQ range names → `where` before `orderby` when filtering → PascalCase names in anonymous projections via aliases.
**Invariant:** custom delegate type with single method matching `Func` fails review.
**Probe:** query readability review; anonymous type properties PascalCase.

## Public API documentation seam
```csharp
/// <summary>
/// Removes the element at the specified index.
/// </summary>
/// <param name="index">The zero-based index of the element to remove.</param>
/// <returns>The removed element.</returns>
public T RemoveAt(int index) { /* ... */ }
```

**Flow:** every public/protected member gets XML summary → parameters/returns documented when non-obvious.
**Invariant:** new public API without `///` summary fails review.
**Probe:** CS1591 or DocFX/doc generation gate on public projects.

## Verdict
Specific exceptions, using disposal, static qualification, Func/Action, XML public docs. Learning note: `csharp-style-learning-note.md`.
