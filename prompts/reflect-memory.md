# Memory reflection

Review this project's accumulated engineering memory and surface what we are actually learning.

Use the `hindsight_reflect` tool against the project bank (default) with a synthesis query covering:

`hindsight_reflect` is registered by the Pi Hindsight extension only. If it is unavailable on this host, stop and report that reflection requires Pi with the Hindsight extension; never substitute speculation for the memory pass.

- repeated decisions and implementation choices
- repeated corrections the user made to the agent
- approaches that failed and why
- approaches that worked especially well
- reused implementations and recurring workflows
- contradictions and obsolete assumptions

If the configured user bank has content, reflect over it too for cross-project recurrence. Pass `global` as the `bank` option so each machine's configured user bank is selected rather than a hardcoded id.

Before proposing any conclusion, actively search memory for counter-evidence. Frequency is evidence, not truth: prefer patterns with independent occurrences, consistently good outcomes, and weak or explainable counterexamples.

Present each candidate pattern in this exact shape:

    Pattern:
    Supporting evidence:
    Counter-evidence:
    Projects involved:
    Observed outcomes:
    Confidence:
    Recommended action:

`Recommended action` must be exactly one of:

- keep as memory only
- emerging preference
- core principle candidate
- repeated workflow -> Skill candidate
- deterministic expectation -> test/gate/CI candidate
- reusable implementation -> code foundation
- project-specific/private knowledge
- contradicted / obsolete -> demote or forget

Rules:

- Do not invent principles. Only report what retained evidence supports.
- Do not turn memories into Skills unless a genuinely repeated PROCEDURE appears.
- If a finding is deterministic (formatting, unused imports, dependency boundaries, invalid exports), recommend a test/lint/CI gate instead of more instructions.
- If a lesson is already embodied in working code, recommend the code as foundation — record only WHY and WHEN it was chosen.
- Do not modify any memory, config, or code during reflection. This is a read-and-report pass.

Focus (optional, defaults to the whole project bank): $ARGUMENTS
