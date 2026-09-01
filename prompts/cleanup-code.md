# Clean up code without changing behavior

Clean up the code in the scope below while preserving behavior.

- Establish the current behavior and tests before editing.
- Remove duplication, dead code, accidental complexity, and AI-shaped structure only when evidence supports it.
- Keep public behavior, data formats, error semantics, and unrelated files unchanged.
- Make the smallest coherent refactor, then run targeted tests and compare the resulting diff.
- If cleanup would require a behavior change, stop and report it instead of smuggling it in.

Scope:
$ARGUMENTS
