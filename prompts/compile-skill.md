# Compile session evidence into a candidate skill

Compile a proven procedure from selected session evidence. This command is an
explicit promotion request, not an automatic end-of-session ritual.

## Qualification

1. Resolve the current or named session evidence and preserve its provenance.
2. Identify the repeated procedure, decisions, failure modes, and successful
   outcome.
3. Search for contradictory evidence.
4. Require independent recurrence by default. A single-session candidate
   qualifies only when the user explicitly requests it and the method was
   unusually costly, high-risk, or difficult to recover.
5. Separate reusable procedure from project-specific facts.
6. Route reusable implementation into code and deterministic expectations into
   tests, lint, validators, or CI rather than prose.
7. If no procedure qualifies, create no files and explain why.

## Authoring

When a skill qualifies:

- Follow `skills/writing-skills/SKILL.md` and the canonical skill template.
- Write the smallest procedure that changes behavior.
- Include no raw transcript, source dump, secret, credential, client identifier,
  or current repository inventory.
- Create it as a hidden/manual candidate with
  `disable-model-invocation: true`.
- Do not make it model-visible without an explicit request and successful
  trigger/collision testing.
- Preserve compact evidence provenance outside the operational instructions
  only when it materially supports future review.
- Run the skill validator, catalog checks, style checks, and affected behavior
  tests.

Outside the universal-template repository, draft in the conversation unless the
user supplies an explicit destination.

## Report

    Evidence used:
    Qualification result:
    Material routed to code or gates:
    Skill created or changed:
    Visibility:
    Verification:
    Material deliberately omitted:

Request:

$ARGUMENTS
