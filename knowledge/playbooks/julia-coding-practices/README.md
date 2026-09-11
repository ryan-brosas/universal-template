---
title: julia-coding-practices
summary: Use when authoring or reviewing Julia, BlueStyle/JuliaFormatter 4-space/92-col layout, explicit using/exports, typed methods with return, kwargs semicolon, docstrings, and formatter/test in CI.
kind: playbook
---

# Julia Coding Practices

Application skill for Julia BlueStyle. When project sets SciMLStyle or custom `.JuliaFormatter.toml`, follow that formatter config first.

## Core Principle

Julia package quality is **formatter-enforced consistency + explicit module APIs**, typed exported methods, qualified extensions, documented surface.

## When to Use / NOT

- Julia packages, libraries, and `.jl` application code (General/Grades).
- Setting up JuliaFormatter, Pkg.test, Documenter in CI.

**NOT when:**

- Generated Julia code, validate generators.
- One-off scripts with no package boundary, apply layout/docs lightly.

## Workflow

1. **Layout**, JuliaFormatter blue, 92 cols.
2. **Modules**, using, exports.
3. **Methods**, return, kwargs, types.
4. **Docs/tests**, docstrings, testset.
5. **Verify**, `JuliaFormatter.format`, `Pkg.test()`, docstring audit on exports.

## Red Flags

- Tabs or trailing whitespace
- `using A, B` combined import
- Bare `import` extension without qualification
- Code outside module block in module files
- Undocumented exported functions
- Long functions without explicit `return`
- `f(x, y=3)` missing semicolon before kwargs
- Type baked into function name (`process_dataframe`)
- Over-concrete public signatures (`Array{Int}` vs `AbstractArray`)
- Mutable non-const globals
- Missing trailing comma in multiline literals
- Padded `f( x )` brackets
- Chained ternary operators
- `for i = 1:n` instead of `in`
- Internal API without `_` prefix
- `@test x == 0.0` visual noise
- Caret-only Project.toml compat (`^0.17`)

## Verification

- `JuliaFormatter.format(".")` with `style = "blue"`
- `julia --project -e 'using Pkg; Pkg.test()'`
- Exported names have docstrings (manual or tool-assisted)
