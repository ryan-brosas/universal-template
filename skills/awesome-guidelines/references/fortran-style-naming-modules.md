<!-- capsule-v2 -->
# Naming and modules — are symbols consistent and exports intentional?

**Source:** stdlib STYLE_GUIDE; fortran90.org; FOSS Best_Practices. **Question:** Can collaborators grep names and see a minimal public surface?

## Naming seam
**Path/Symbol:** modules, procedures, variables in `.f90` sources.
**Signature:** lowercase identifiers; underscores between words; explicit `intent`.
**Data Shape:** `private` default + `public ::` export list.

### Decisive pattern
```fortran
module spline_interp
use types, only: dp
implicit none
private
public :: spline_interpolate

contains

    subroutine spline_interpolate(x, y, xq, yq, has_failed)
        real(dp), intent(in) :: x(:), y(:), xq(:)
        real(dp), intent(out) :: yq(:)
        logical, intent(out) :: has_failed
        ...
    end subroutine spline_interpolate

end module spline_interp
```

**Flow:** lowercase Fortran keywords and names → multi-word names use underscores (`has_failed`) except conventional shortenings (`linspace`) → math symbols may stay compact (`Rnl`, `Gamma`) → logicals describe state (`lib_is_initialized`) → defined operators use `.camelCase.` not `.not_foo.` → modules start with `implicit none`, default `private`, enumerate `public ::` exports → `use other, only: sym` — avoid bare `use other`.
**Invariant:** camelCase procedures, missing `intent`, blanket `use`, or exporting entire module by default fails review.
**Probe:** grep `use [a-z_]+$` without `only`; intent audit on all dummy args; public API list review.

## Attribute seam
```fortran
real, allocatable :: grid(:), field(:, :)
```
**Flow:** declare allocatable as `name(:)` / `name(:,:)` — reserve `dimension` attribute only when many same-rank arrays share shape and it reduces noise → `optional` follows `intent`.
**Invariant:** verbose `dimension(:), allocatable` when simple `(:)` form works fails review.
**Probe:** style grep `dimension\(:`

## Verdict
Lowercase snake_case, private modules, explicit imports, mandatory intent. Learning note: `fortran-style-learning-note.md`.
