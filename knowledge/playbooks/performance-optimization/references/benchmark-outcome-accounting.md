# Account for benchmark outcomes across arms and attempts

Use when a batch compares conditions (models, handoff on/off, harness variants)
across tasks and you intend to report a rate, cost or comparison. Freezing the
command is not freezing the experiment.

## Freeze the task by arm matrix

Record before launch: the task set, the arms, and for every cell the intended
model, runtime and configuration. Then record what was observed. A configured
label is not observed identity; when the runner cannot report which model served
a request, mark the cell unknown rather than assuming it matched.

Track a small state per attempt - scheduled, launched, request observed, artifact
captured, graded, compared - instead of one completed flag. Attempts that were
skipped, aborted or never started stay in the record with their reason.

## Prove the cell, not the wiring

A handoff, tool call or transport canary proves plumbing; it does not prove the
task was solved, so it cannot fill a task cell. Require the arm's own independent
verification of the produced artifact before counting a cell as a result, and
keep "the mechanism works" separate from "this task passed".

## Classify failures by their experimental role

Name each control's expected outcome before grading:

- **gold**: the known-good patch resolves its required tests;
- **no-op**: the unchanged task fails, typically a compile/import failure of code
  the patch introduces, with the test command demonstrably executed;
- **candidate failure**: the attempt's own broken code, counted against it;
- **infrastructure**: environment, tooling or harness fault, not attributable to
  the attempt;
- **unobserved**: insufficient evidence to place it.

Require affirmative evidence that the check ran, and prefer a named mechanism
over a loose error substring. Preserve raw grader output unchanged and publish a
corrected classification beside it rather than editing the record. An expected
no-op failure is not a broken grader, and a candidate's syntax error is not an
infrastructure skip.

## Keep the schedule as the denominator

Close every attempt onto the frozen schedule and report the full attempted
population - including failures, timeouts and unsettled usage - before any
comparison; failed attempts consumed time and money too.

If a helper advertises intent-to-treat, verify which rows actually reach it.
Filtering to attempts with observed requests, or summing only over comparable
pairs, silently changes the denominator. Report completed pairs, the evaluable
subset and censored or unresolved arms as separately named counts. Recorded scope
changes are provenance: a narrowed plan does not show that the original schedule
executed.

## Boundaries

A delivered model switch is not a review. Returning to a main model proves which
model is selected, not that it verified anything; if independent review is the
policy, require its own evidence. Do not treat one arm's advantage on a few
comparable pairs as superiority.
