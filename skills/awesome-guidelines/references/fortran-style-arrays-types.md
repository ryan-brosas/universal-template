<!-- capsule-v2 -->
# Arrays and types — are numerics and memory layout idiomatic?

**Source:** fortran90.org best-practices §Arrays/Multidimensional; stdlib attributes. **Question:** Do array interfaces avoid copies and kind mistakes?

## Array seam
**Path/Symbol:** procedure dummy arguments and numerical kernels.
**Signature:** assumed-shape `r(:)`; `real(dp)` kind; `_dp` literals.
**Data Shape:** innermost index leftmost for contiguous access.

### Decisive pattern
```fortran
module integrate_mod
use types, only: dp
implicit none

contains

    subroutine trapezoid(f_values, dx, integral)
        real(dp), intent(in) :: f_values(:)
        real(dp), intent(in) :: dx
        real(dp), intent(out) :: integral
        integer :: i, n

        n = size(f_values)
        integral = 0.5_dp * (f_values(1) + f_values(n))
        do i = 2, n - 1
            integral = integral + f_values(i)
        end do
        integral = integral * dx
    end subroutine trapezoid

end module integrate_mod
```

**Flow:** export `integer, parameter :: dp = kind(0.d0)` (or use shared `types` module) → declare reals as `real(dp)` → float literals always `1.0_dp` → pass arrays assumed-shape with `intent` — no size args unless C/LAPACK/legacy → return arrays via `function f(n) result(r)` with explicit shape when needed → for multidimensional work keep fastest index left: prefer `A(:, i)`, `A(:, :, k)` in hot loops → promote to `real(dp)` before `/` when float division required → prefer `allocatable` over pointers for owned buffers.
**Invariant:** `real*8`, bare `1.0/2` integer division, explicit-shape copies in pure Fortran paths, or `A(i,:,:)` stride in inner loops fails review.
**Probe:** kind audit; assumed-shape grep on internal procedures; loop slice orientation review.

## Elemental seam
**Flow:** use `elemental`/`pure` functions when operating scalar-wise on arrays; fall back to vector wrappers + `reshape` only when algorithm needs array ops inside.
**Invariant:** non-pure elemental candidate fails review.
**Probe:** `pure`/`elemental` attribute check.

## Verdict
dp kind, assumed-shape, contiguous slices, allocatable ownership. Learning note: `fortran-style-learning-note.md`.
