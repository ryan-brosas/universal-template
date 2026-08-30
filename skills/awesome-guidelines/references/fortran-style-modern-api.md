<!-- capsule-v2 -->
# Modern API — is the code standard-conforming and documented?

**Source:** stdlib STYLE_GUIDE §Use modern Fortran, FORD; FOSS Best_Practices §standard compliance. **Question:** Will the public API survive stdlib-style CI and consumer expectations?

## Modern seam
**Path/Symbol:** library public modules and `doc/` specs.
**Signature:** F2003+ features only; FORD docs on public/protected symbols.
**Data Shape:** no obsolescent/vendor constructs.

### Decisive pattern
```fortran
!> Generate evenly spaced values between START and STOP.
!! @param start First value
!! @param stop Last value
!! @param n Number of samples
function linspace(start, stop, n) result(x)
    real(dp), intent(in) :: start, stop
    integer, intent(in) :: n
    real(dp) :: x(n)
    ...
end function linspace
```

**Flow:** ban obsolescent features (`common`, `pause`, `entry`, arithmetic `if`, computed `goto`) → ban vendor syntax (`real*8`, non-standard intrinsics like `etime()`) → document every public/protected entity with FORD (`doc/` + wiki conventions) → place design specs in `doc/specs/` when adding new stdlib-style proposals → prefer standard `ISO_C_BINDING` over ad hoc C interop when extensions needed → surface failures loudly (`stop_error` / structured error flags) instead of silent `_ =` ignore patterns.
**Invariant:** obsolescent construct, undocumented public symbol, or undocumented vendor extension fails stdlib-grade review.
**Probe:** compiler standard-conformance flags; FORD build; grep obsolescent keywords.

## Tooling seam
**Flow:** enforce fprettify in CI alongside build/tests → keep specs and API docs co-located with modules.
**Invariant:** public API change without FORD doc update fails review.
**Probe:** CI fprettify + FORD gate; doc diff on exported symbols.

## Verdict
Modern Fortran subset, FORD-documented public API, formatter in CI. Learning note: `fortran-style-learning-note.md`.
