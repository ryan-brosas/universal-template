# Reflect on selected session evidence

Derive temporary, evidence-linked lessons from one explicitly bounded set of
session events.

## Source selection

Use the current session when no historical session is named. For historical
reflection, use project-scoped raw session JSONL or an explicitly supplied
transcript. A projection provider may assist only when its conclusions remain
traceable to the source events.

If the requested historical evidence is inaccessible, report the missing source
and stop. Do not substitute a speculative retrospective.

## Reflection

Extract only what the selected evidence supports:

- objective and constraints
- decisions and rejected alternatives
- attempts that failed and why
- user corrections
- approaches that worked
- tests, tool results, and observed outcomes
- contradictions and obsolete assumptions
- unresolved uncertainty

Check current source when a lesson makes a claim about present code. Search the
selected evidence for counterexamples before assigning confidence.

Present each candidate in this form:

    Lesson:
    Supporting evidence:
    Counter-evidence:
    Scope:
    Observed outcome:
    Current-source status:
    Confidence:
    Suggested disposition:

`Suggested disposition` must be one of:

- leave in session history
- reusable implementation -> CODE candidate
- deterministic lesson -> GATE candidate
- repeated procedure -> SKILL candidate
- critical rationale -> PROJECT NOTE candidate
- not worth saving
- contradicted or obsolete

## Rules

- This is a read-only projection.
- Do not create or modify code, notes, memory, skills, foundations, indexes, or
  configuration.
- Frequency is evidence, not truth.
- Do not turn a current code fact into historical memory.
- Do not recommend a skill for a generic observation or one-off preference.
- Do not use global or cross-project history unless explicitly requested.
- Treat this output as disposable until the user deliberately promotes part of
  it.

Focus:

$ARGUMENTS
