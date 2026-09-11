# Fortran style — learning note

**Status:** deep ingest (2026-08-28). **Feeds:** `fortran-style-*.md` capsules, `fortran-coding-practices` application skill.

## Sources read

| Source | What we extracted |
|---|---|
| [fortran-lang/stdlib STYLE_GUIDE.md](https://github.com/fortran-lang/stdlib/blob/master/STYLE_GUIDE.md) (primary) | modern standard Fortran; file naming; 4-space indent; 80/132 cols; lowercase snake_case; intent on dummies; allocatable `a(:)` not dimension attribute; end name labels; FORD docs; fprettify in CI |
| [fortran90.org best-practices](https://fortran90.org/best-practices.html) (secondary) | lowercase keywords; `dp` kind parameter; explicit `use … only`; module private-by-default + public list; assumed-shape arrays; column-major slice access; avoid obsolescent features |
| [Fortran-FOSS-Programmers/Best_Practices](https://github.com/Fortran-FOSS-Programmers/Best_Practices) (secondary) | explicit over implicit; consistent naming; logical names like `lib_is_initialized`; standards compliance with practical extensions via `ISO_C_BINDING` |

**Not duplicated here:** Full OpenMP/OpenACC patterns — use HPC foundations. Every fprettify flag — follow project `.fprettify` config.

## Mental model

Fortran style in the fortran-lang ecosystem is **modern-standard + scientific readability**:

1. **Modern language** — F2003+ idioms; no `common`, `goto`, `real*8`, vendor intrinsics.
2. **Layout** — 4 spaces, ≤80 cols (hard max 132), fprettify; one module/program per file.
3. **Naming** — lowercase keywords and identifiers; underscores between words; math symbols may stay short (`Ylm`).
4. **Modules** — `implicit none`; explicit `use … only`; narrow `public` export list.
5. **Procedures** — always `intent`; assumed-shape `r(:)` defaults; `real(dp)` + `_dp` literals.
6. **Docs** — FORD docstrings on public/protected API.

## Decision tables

### Files & layout

| Topic | Rule |
|---|---|
| Extension | `.f90` / `.F90` (preprocess) |
| One entity | one `module`/`program` per source file |
| Filename | matches module/program name |
| Submodule impl | `foo.f90` + `foo_implementation.f90` |
| Includes | `.inc` under `include/` |
| Tests | `test/test_<module>.f90` |
| Indent | 4 spaces, no tabs |
| Line length | should ≤80; must ≤132 |
| End labels | `end module foo` when block > ~25 lines |

### Naming

| Entity | Convention |
|---|---|
| Keywords | lowercase (`subroutine`, `do`) |
| Variables/procedures | lowercase; `has_failed` not `hasfailed` |
| Math symbols | short notation OK (`Gamma`, `Rnl`) |
| Logicals | descriptive (`lib_is_initialized`) |
| Files | match primary module name |
| Operators | `.camelCase.` when defined (no underscores in op name) |

### Modules & attributes

| Topic | Rule |
|---|---|
| Implicit | `implicit none` in every module/program |
| Visibility | default private; explicit `public :: …` |
| Imports | `use mod, only: sym` — not blanket `use mod` |
| Intent | always on dummy arguments |
| Optional | follows `intent` |
| Arrays | `real, allocatable :: a(:)` preferred over `dimension` attribute |
| Module procedures | `<attrs> module subroutine name` (pre-CMake 3.25 compat) |

### Arrays & numerics

| Case | Rule |
|---|---|
| Pass arrays | assumed-shape `intent(in/out) :: r(:)` default |
| Explicit-shape | C/LAPACK interop or function result only |
| Storage | innermost index left; slices `A(:, i)` contiguous |
| Kind | export `integer, parameter :: dp = kind(0.d0)` |
| Literals | `1.0_dp`, `3.5e8_dp` — always `_dp` suffix |
| Integer div | promote one operand to `real(dp)` when float division needed |
| Allocatable | prefer over pointers for auto deallocation |

### API & tooling

| Topic | Rule |
|---|---|
| Docs | FORD on public/protected entities |
| Format | fprettify in CI (`fprettify -r` or project config) |
| Obsolete | no `common`, `pause`, `entry`, arithmetic `if`, computed `goto` |
| Vendor | no `real*8`, non-standard intrinsics |
| Errors | structured stops/errors (`stop_error` pattern) vs silent continue |

## Anti-patterns

- Tabs or lines >132 characters
- Missing `intent` on dummy arguments
- Blanket `use module` without `only`
- `-compile(export_all)` equivalent: exporting everything by default without `private`
- `dimension(:)` attribute when `a(:)` suffices
- `real*8` or implicit typing
- Obsolescent Fortran features
- Trailing whitespace
- Public API without FORD docs
- Column on wrong side in hot loops (`A(i, :, :)` when innermost should be left)
- Magic numeric literals without `parameter` or `_dp`
- Multiple modules crammed in one file

## Skill trace

| Artifact | Role |
|---|---|
| `fortran-style-formatting-layout.md` | indent, cols, files, fprettify |
| `fortran-style-naming-modules.md` | names, modules, use/intent |
| `fortran-style-arrays-types.md` | assumed-shape, dp, storage order |
| `fortran-style-modern-api.md` | modern std, FORD, obsolescence |
| `fortran-coding-practices/SKILL.md` | fprettify/FORD/build/test in CI |
