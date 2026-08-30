<!-- capsule-v2 -->
# Declarations and API — are types, properties, and operators idiomatic?

**Source:** D Style §Type Aliases, §Declaration Style, §Properties, §Operator Overloading. **Question:** Is public API readable without UFCS or operator surprises?

## Declaration seam
**Path/Symbol:** type aliases, variable declarations, public functions.
**Signature:** `alias New = Old;` left-associative decls; explicit return types.
**Data Shape:** property functions instead of get/set pairs.

### Decisive pattern
```d
alias Callback = int function(string) pure nothrow;

int[] buffer, scratch;   // same type — left justified
int** pp, qq;

@property int length() const { return _length; }

@property void length(int value)
{
    _length = value;
}
```

**Flow:** prefer `alias T = U` assignment syntax → declare related vars with shared type left (`int[] x, y`) → explicit return types on public functions → use `@property` nouns instead of `getLength`/`setLength` → getters must not mutate state.
**Invariant:** C-style `int []x`, meaningless `alias INT = int`, or getter with side effects fails review.
**Probe:** API review; compiler `@property` usage audit.

## UFCS and operators seam
```d
import std.stdio;
import std.range;

void main()
{
    writeln("hello");
    iota(0, 10).dropOne.array.front.writeln;
}
```

**Flow:** UFCS for range pipelines OK → use regular call syntax for side-effect functions (`writeln("hello")` not `"hello".writeln`) → operator overloads keep conventional meaning (`+` adds, `<<` shifts).
**Invariant:** `"hello".writeln` or `+` meaning unrelated to addition fails review.
**Probe:** grep UFCS on known side-effect APIs; operator review on user-defined types.

## Verdict
alias= syntax, left-justify decls, properties, conservative UFCS/operators. Learning note: `d-style-learning-note.md`.
