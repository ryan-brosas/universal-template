<!-- capsule-v2 -->
# Formatting and layout — is whitespace mechanical and diff-friendly?

**Source:** fortran-lang stdlib STYLE_GUIDE; fprettify. **Question:** Will CI format checks and reviewers see semantics, not spacing debates?

## Layout seam
**Path/Symbol:** `src/**/*.f90`, `test/test_*.f90`.
**Signature:** 4-space indent; ≤80 cols preferred (≤132 max); one module per file.
**Data Shape:** filename matches module/program name.

### Decisive pattern
```fortran
module linspace_mod
implicit none
private
public :: linspace

contains

    function linspace(start, stop, n) result(x)
        real(dp), intent(in) :: start, stop
        integer, intent(in) :: n
        real(dp) :: x(n)
        integer :: i

        do i = 1, n
            x(i) = start + (stop - start) * real(i - 1, dp) / real(n - 1, dp)
        end do
    end function linspace

end module linspace_mod
```

**Flow:** run fprettify before commit (project `.fprettify` or `--indent 4`) → indent every construct body 4 spaces → keep lines ≤80 when feasible, never >132 → no tab characters → strip trailing whitespace → one `module`/`program` per `module_name.f90` → submodule impl as `module_implementation.f90` → tests as `test/test_module_name.f90` → label distant `end module name` / `end subroutine name`.
**Invariant:** tabs, >132-char lines, trailing ws, or mismatched file/module names fail stdlib CI style.
**Probe:** fprettify diff; line-length grep; filename vs `module` name check.

## Include seam
**Flow:** `.inc` files only in `include/` → `.F90` when preprocessing required.
**Invariant:** random `.h` includes or multiple top-level modules per file fails review.
**Probe:** tree layout review; one-module-per-file grep.

## Verdict
fprettify, 4-space indent, 80/132 rule, one module per file. Learning note: `fortran-style-learning-note.md`.
