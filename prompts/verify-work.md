# Verify the current work

Verify the current work for the scope below.

Treat the requested checks or concern as signals about risk, not a predetermined verification plan. Optimize for confidence, coverage of material behavior, and evidence quality while reducing redundant checks, ceremony, runtime, and side effects. Do not gain speed by leaving important acceptance conditions untested.

Inspect the actual change and use your judgment to select the smallest decisive tests and behavioral probes. Run them, investigate failures to root cause, and report exact commands, outcomes, untested paths, and remaining risk.

Do not modify files or external state unless the request explicitly asks for a fix.

## Reusable context

- Trust runtime evidence over claims: run the smallest decisive test and report its real output.
- Cover material behavior; skip redundant suites and state untested paths plainly.
- A failing check is evidence of a defect, not a reason to weaken it; investigate to root cause first.
- Where a property is mechanically checkable, prefer the gate and record its command and exit, not a hand-wave.

Scope:
$ARGUMENTS
