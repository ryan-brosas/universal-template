# Review the current work

Review the current changes for the scope below.

Treat the stated concern as a lead, not a conclusion. Optimize for stronger defect detection, actionability, and evidence while reducing false positives, noise, and behavioral steering. Do not improve brevity by hiding material risk or improve coverage by reporting speculative findings.

Inspect the actual diff and enough surrounding code to judge correctness, regressions, security, interfaces, tests, configuration, documentation, and complexity. Use your judgment about what is material. Report only actionable, evidence-backed findings, ordered by severity, with precise locations and a concrete fix or reproduction path.

Do not edit files, rewrite history, or claim checks you did not run.

## Reusable context

- Judge the actual code, callers, tests, and runtime, not the summary: source and observed behavior decide what is material.
- Flag only actionable findings with a precise location and a concrete fix; suppress noise and unsupported speculation.
- Weight correctness, security, and regression risk over style; a claim without evidence is a question, not a verdict.
- Prefer proposed checks or tests as the fix where they exist; a silent assertion is worth less than a run that fails.

Scope:
$ARGUMENTS
