<!-- capsule-v2 -->
# Modern idioms — is C# used idiomatically for current language versions?

**Source:** C# coding conventions §Language guidelines, §String data, §Arrays. **Question:** Does code prefer modern constructs where they improve clarity?

## var and types seam
**Path/Symbol:** application C# code (non-generated).
**Signature:** language keywords for types; `var` only when type obvious.
**Data Shape:** collection expressions; target-typed `new`.

### Decisive pattern
```csharp
string message = "This is clearly a string.";
int iterations = Convert.ToInt32(Console.ReadLine());

var invoice = new Invoice(id, total);
InvoiceProcessor processor = new();

string[] vowels = ["a", "e", "i", "o", "u"];

foreach (char ch in message)
{
    Process(ch);
}
```

**Flow:** explicit types when not obvious → `var` for `new`/literals/casts → `foreach` with explicit element type → collection expressions for initialization → target-typed `new()` when variable type matches.
**Invariant:** `var inputInt = Console.ReadLine()` and `var` in `foreach` fail review.
**Probe:** IDE0007/IDE0008 analyzer configuration matches team policy on changed files.

## Strings and logic seam
```csharp
var displayName = $"{customer.LastName}, {customer.FirstName}";

var path = """
    C:\data\input.txt
    """;

if ((divisor != 0) && (dividend / divisor is var quotient))
{
    Console.WriteLine($"Quotient: {quotient}");
}
```

**Flow:** interpolation for concatenation → raw string literals for paths/multiline → `&&`/`||` for boolean short-circuit → `StringBuilder` in tight loops appending many times.
**Invariant:** `&`/`|` for boolean conditions and `$"..." +` chains in loops fail review.
**Probe:** grep `&&` in guard conditions; no `+` string concat inside hot loops in diff.

## Initialization seam
```csharp
public record Person(string FirstName, string LastName);

public class LabelledContainer<T>(string label)
{
    public string Label { get; } = label;

    public required T Contents { get; init; }
}
```

**Flow:** records use PascalCase primary ctor params → classes use camelCase primary ctor params → prefer `required` init properties over manual ctor validation when appropriate.
**Invariant:** mutable init of required domain fields without `required`/ctor fails review.
**Probe:** nullable/reference analysis clean; required members enforced at compile time.

## Verdict
Modern C# — explicit when unclear, var when obvious, collection expressions, safe boolean ops. Learning note: `csharp-style-learning-note.md`.
