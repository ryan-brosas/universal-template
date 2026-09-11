<!-- capsule-v2 -->
# Formatting and layout — is BlueStyle mechanical and diff-clean?

**Source:** invenia/BlueStyle §Whitespace, Synopsis; JuliaFormatter. **Question:** Will JuliaFormatter blue mode and reviewers agree on layout?

## Layout seam
**Path/Symbol:** `src/**/*.jl`, `test/runtests.jl`.
**Signature:** 4-space indent; 92-column limit; trailing commas in expanded forms.
**Data Shape:** `.JuliaFormatter.toml` with `style = "blue"`.

### Decisive pattern
```julia
arr = [
    1,
    2,
    3,
]

constraint = conic_form!(
    SOCElemConstraint(temp2 + temp3, temp2 - temp3, 2 * temp1),
    unique_conic_forms,
)
```

**Flow:** configure `style = "blue"` in `.JuliaFormatter.toml` → 4 spaces, no tabs → limit lines to 92 chars → no trailing whitespace → no padding inside parentheses (`Int64(x)` not `Int64( x )`) → spaces around binary operators; no space before unary `-` → multiline arrays/calls use trailing comma → break long calls with bracket lines aligned, args indented one level → no blank line immediately inside `function`/`end` body edges.
**Invariant:** tabs, >92 default lines without break, missing trailing comma in expanded literals, or padded brackets fails BlueStyle review.
**Probe:** `JuliaFormatter.format(".")`; ruler at 92; diff review.

## Block spacing seam
**Flow:** one blank line between distinct multi-line blocks; group related one-liners; separate multiline `if` and `for` with blank line.
**Invariant:** double-spacing between one-line method defs fails review.
**Probe:** formatter output; blank-line heuristic check.

## Verdict
JuliaFormatter blue, 92 cols, trailing commas, tight brackets. Learning note: `julia-style-learning-note.md`.
