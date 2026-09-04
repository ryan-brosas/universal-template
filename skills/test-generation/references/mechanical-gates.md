# Mechanical gate ladder

Source: scarywood75, 2026-07-19; distilled from the original discussion
transcript and qualified against this repository's engineering policy.

## Gate exact, valuable invariants

A deterministic, reproducible failure class can earn a test or gate: invalid
references, nonexistent constants, unused exports where the project forbids
them, generated-file drift, or exact structural duplication. The gate should
check an artifact or runtime property, not whether an agent followed a preferred
thinking process.

Do not mechanize every possible check. Add a gate when recurrence, impact, and
signal justify its maintenance and false-positive cost.

## Quality packs

A quality pack can group a small set of related gates. A project-wide pack may
own exact repository invariants while language-specific packs own compiler,
linter, or test-runner contracts. Keep each check independently diagnosable and
allow documented exceptions where the underlying policy allows them.

## Gates versus prompts

The source recommended blocking progress until an agent called a researcher.
That enforces ceremony rather than evidence and is not adopted here. If research
quality matters, verify the resulting claim, citation, artifact, or behavior.
Tool choice remains contextual.

## Applying

- Promote a repeated deterministic catch into the narrowest maintained test or
  gate that owns it.
- Keep semantic review, research strategy, and tool selection as judgment.
- A red required gate blocks completion until fixed or dispositioned through the
  project's explicit exception path; do not waive it silently.
