<!-- capsule-v2 -->
# Functions and methods — are signatures typed and returns explicit?

**Source:** BlueStyle §Function Naming, Method Definitions, Keyword Arguments, Type annotation. **Question:** Do method names, types, and kwargs read clearly at call sites?

## Method seam
**Path/Symbol:** function definitions and external calls.
**Signature:** snake_case action names; types in signature; long-form `return`.
**Data Shape:** semicolon before keyword arguments at call site.

### Decisive pattern
```julia
submit(bid::Bid) = queue!(bid)

function foobar(
    df::DataFrame,
    id::Symbol,
    variable::Symbol,
    value::AbstractString;
    prefix::AbstractString = "",
)
    result = transform_row(df, id, variable, value, prefix)
    return result
end

xy = foo(x; y = 3)
```

**Flow:** encode domain types in arguments not function name (`submit(bid::Bid)` not `submit_bid`) → one-line `f(x) = …` only if ≤92 cols → long functions use `function`/`end` with explicit `return` (including `return nothing`) → break parameter lists one per line when over 92 cols → prefer general types (`AbstractArray`, `Integer`) in public signatures → call with semicolon before kwargs: `f(x; y=3)` → ternary single-line; use `if`/`elseif` for chains → `for x in xs` not `=` or `∈`.
**Invariant:** implicit long-function return, kwargs without `;`, concrete `Array{Int}` when `AbstractArray` suffices, or chained ternaries fails review.
**Probe:** JuliaFormatter + manual kwargs/return audit; type generality spot check.

## Float literal seam
```julia
x = 0.1
y = 2.0
```

**Flow:** always include leading/trailing zero in floats.
**Invariant:** `.1` or `2.` literals fail review.
**Probe:** numeric literal grep.

## Verdict
Typed general signatures, explicit return, semicolon kwargs, snake_case actions. Learning note: `julia-style-learning-note.md`.
