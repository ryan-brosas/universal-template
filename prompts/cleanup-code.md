# Clean up code without changing behavior

Clean up the code in the scope below while preserving behavior.

Treat the user's concern as a signal, not a predetermined refactor. Optimize for greater clarity, maintainability, and consistency with less duplication, accidental complexity, and maintenance burden. Do not improve those qualities by materially degrading capability, correctness, performance, public behavior, data formats, or error semantics.

Establish the relevant behavior before editing. Use your judgment to choose worthwhile simplifications and leave code alone when change would not produce a clear net improvement. Preserve unrelated files.

Implement the cleanup, then run targeted tests and behavioral probes and inspect the resulting diff. If a valuable improvement requires a behavior change, report the boundary instead of hiding the change inside cleanup.

Scope:
$ARGUMENTS
