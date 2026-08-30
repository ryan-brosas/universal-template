<!-- capsule-v2 -->
# Docs and tests — are exports documented and tests structured?

**Source:** BlueStyle §Comments, Documentation, Test Formatting, Performance. **Question:** Can users and CI understand API intent without reading implementation?

## Documentation seam
**Path/Symbol:** exported functions, types, test harness.
**Signature:** Markdown docstrings at 92 cols; intent comments.
**Data Shape:** root `@testset` in `runtests.jl`.

### Decisive pattern
```julia
"""
    predict(model, features) -> Vector

Apply a fitted `model` to `features` and return point predictions.

# Arguments
- `model`: trained model object
- `features`: feature matrix as `AbstractMatrix`
"""
function predict(model, features)
    ...
end

# Compensate for off-by-one border in upstream feed.
x = x + 1
```

```julia
@testset "ExamplePackage" begin
    include("arithmetic.jl")
    include("utils.jl")
end
```

**Flow:** docstring every exported function/type (wrap at 92) → document function once, not every method unless behavior diverges → comments explain intent, not obvious code → capitalize comment sentences; two spaces before `#` inline → tests: single root `@testset` including subfiles → `@test value == 0` without spurious `.0` → minimize globals for performance; use `const` and wrap logic in functions.
**Invariant:** undocumented export, obsolete comment, or scattered top-level test files without root set fails package review.
**Probe:** Documenter/docstring coverage; `@testset` structure review; exported symbol doc grep.

## Project.toml seam
**Flow:** version specs without redundant caret (`DataFrames = "0.17"` not `"^0.17"`).
**Invariant:** caret-only noise in compat section fails consistency check.
**Probe:** Project.toml compat review.

## Verdict
Exported docstrings, intent comments, root testset, lean globals. Learning note: `julia-style-learning-note.md`.
