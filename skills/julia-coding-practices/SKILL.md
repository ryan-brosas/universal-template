---
name: julia-coding-practices
description: "Use when authoring or reviewing Julia — BlueStyle/JuliaFormatter 4-space/92-col layout, explicit using/exports, typed methods with return, kwargs semicolon, docstrings, and formatter/test in CI."
disable-model-invocation: true
---

# Julia Coding Practices

Application skill for Julia BlueStyle learning (from the archived `awesome-guidelines` style capsules). When project sets SciMLStyle or custom `.JuliaFormatter.toml`, follow that formatter config first.

## Core Principle

Julia package quality is **formatter-enforced consistency + explicit module APIs** — typed exported methods, qualified extensions, documented surface.

## When to Use / NOT

- Julia packages, libraries, and `.jl` application code (General/Grades).
- Setting up JuliaFormatter, Pkg.test, Documenter in CI.

**NOT when:**

- Generated Julia code — validate generators.
- One-off scripts with no package boundary — apply layout/docs lightly.

## Workflow

1. **Layout** — JuliaFormatter blue, 92 cols (`julia-style-formatting-layout.md`).
2. **Modules** — using, exports (`julia-style-modules-imports.md`).
3. **Methods** — return, kwargs, types (`julia-style-functions-methods.md`).
4. **Docs/tests** — docstrings, testset (`julia-style-docs-tests.md`).
5. **Verify** — `JuliaFormatter.format`, `Pkg.test()`, docstring audit on exports.

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
- Capsule checklist on main module exports

## Skill Result Contract

```xml
<skill_result>
  <skill>julia-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>jl diff, JuliaFormatter/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>accidental implicit return, global perf hit, API drift, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/julia-style-learning-note.md`
- `awesome-guidelines/references/julia-style-formatting-layout.md`
- `awesome-guidelines/references/julia-style-modules-imports.md`
- `awesome-guidelines/references/julia-style-functions-methods.md`
- `awesome-guidelines/references/julia-style-docs-tests.md`
