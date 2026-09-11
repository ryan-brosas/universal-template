---
title: fortran-coding-practices
summary: Use when authoring or reviewing Fortran, fprettify 4-space layout, lowercase snake_case, intent/assumed-shape, dp kind, private modules, FORD docs, modern F2003+ only, and build/fprettify/test in CI.
kind: playbook
---

# Fortran Coding Practices

Application skill for Fortran style. For HPC parallelism (OpenMP/OpenACC), consult the domain library's own source or docs.

## Core Principle

Fortran quality is **modern-standard clarity**, explicit modules, assumed-shape data, mechanical formatting, and documented public APIs.

## When to Use / NOT

- Fortran scientific libraries, stdlib-style packages, `.f90` application code.
- Setting up fprettify, FORD, gfortran/ifx build, and test harness in CI.

**NOT when:**

- Legacy fixed-form `.f` without modernization plan, migrate first or scope narrowly.
- Generated LAPACK interfaces, validate generators.

## Workflow

1. **Layout**, fprettify, files, indent.
2. **Modules**, names, intent, exports.
3. **Arrays**, dp, assumed-shape, storage.
4. **API**, modern std, FORD.
5. **Verify**, fprettify, `ford`, compiler warnings, tests on changed units.

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
