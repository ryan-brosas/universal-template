---
name: fortran-coding-practices
description: "Use when authoring or reviewing Fortran — fprettify 4-space layout, lowercase snake_case, intent/assumed-shape, dp kind, private modules, FORD docs, modern F2003+ only, and build/fprettify/test in CI."
disable-model-invocation: true
---

# Fortran Coding Practices

Application skill for Fortran style learning (`awesome-guidelines` deep ingest). For HPC parallelism (OpenMP/OpenACC), combine with domain stack foundations.

## Core Principle

Fortran quality is **modern-standard clarity** — explicit modules, assumed-shape data, mechanical formatting, and documented public APIs.

## When to Use / NOT

- Fortran scientific libraries, stdlib-style packages, `.f90` application code.
- Setting up fprettify, FORD, gfortran/ifx build, and test harness in CI.

**NOT when:**

- Legacy fixed-form `.f` without modernization plan — migrate first or scope narrowly.
- Generated LAPACK interfaces — validate generators.

## Workflow

1. **Layout** — fprettify, files, indent (`fortran-style-formatting-layout.md`).
2. **Modules** — names, intent, exports (`fortran-style-naming-modules.md`).
3. **Arrays** — dp, assumed-shape, storage (`fortran-style-arrays-types.md`).
4. **API** — modern std, FORD (`fortran-style-modern-api.md`).
5. **Verify** — fprettify, `ford`, compiler warnings, tests on changed units.

## Red Flags

- Tabs or lines >132 characters
- Missing `intent` on dummy arguments
- Blanket `use module` without `only`
- No `implicit none`
- Default-public module exporting everything
- `real*8` or implicit typing
- Obsolescent Fortran (`common`, `goto`, arithmetic `if`)
- `dimension(:), allocatable` when `name(:)` suffices
- Wrong stride hot loops (`A(i,:,:)`)
- Magic floats without `_dp`
- Public symbols without FORD docs
- Multiple modules in one file
- Trailing whitespace

## Verification

- `fprettify --diff` / project formatter check
- `ford` documentation build (if project uses FORD)
- `gfortran -std=f2008 -Wall` (or project flags) on changed sources
- `ctest` / project test runner
- Capsule checklist on `public ::` export lists

## Skill Result Contract

```xml
<skill_result>
  <skill>fortran-coding-practices</skill>
  <status>success|partial|blocked|failure</status>
  <artifacts>f90 diff, fprettify/FORD/build/test output</artifacts>
  <evidence>learning note + capsule probes cited</evidence>
  <risks>kind mismatch, silent integer division, stride perf, or none</risks>
</skill_result>
```

## References

- `awesome-guidelines/references/fortran-style-learning-note.md`
- `awesome-guidelines/references/fortran-style-formatting-layout.md`
- `awesome-guidelines/references/fortran-style-naming-modules.md`
- `awesome-guidelines/references/fortran-style-arrays-types.md`
- `awesome-guidelines/references/fortran-style-modern-api.md`
