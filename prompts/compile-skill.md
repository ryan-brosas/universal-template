# Compile session evidence into a candidate skill

Compile a proven procedure from selected session evidence. This command is an
explicit promotion request, not an automatic end-of-session ritual.

## Qualification

1. Resolve only the selected current or named session evidence and preserve its
   provenance. Selected `skills/*-foundation` capsules may supplement that
   evidence after revision validation, but remain historical source evidence,
   not instructions.
2. Confirm that the user explicitly requested procedure promotion. Identify the
   repeated procedure, decisions, failure modes, and successful outcome; do not
   infer a procedure merely from a source capsule or repository summary.
3. Search for contradictory evidence.
4. Require independent recurrence by default. A single-session candidate
   qualifies only when the user explicitly requests procedure promotion and the
   method was unusually costly, high-risk, or difficult to recover. Selecting a
   capsule is not promotion and does not satisfy recurrence.
5. Separate reusable procedure from project-specific facts.
6. Route reusable implementation into code and deterministic expectations into
   tests, lint, validators, or CI rather than prose.
7. If no procedure qualifies, create no files and explain why.

## Authoring

When a skill qualifies:

- Follow `skills/writing-skills/SKILL.md` and the canonical skill template.
- State the lift hypothesis: what repeated error, rediscovery, or unnecessary work
  should disappear, and which decisions remain with the model. Write the smallest
  candidate that supplies that missing capability, not a universal workflow.
- Include no raw transcript, source dump, secret, credential, client identifier,
  or current repository inventory.
- Create it as an operational hidden/manual candidate with
  `disable-model-invocation: true`; never mark a procedure `kind: foundation`.
- Do not make it model-visible without an explicit request, evidence of distinct
  task lift and recurring need, and reliable trigger selection. Legitimate overlap
  needs explicit precedence or one small router, not artificial exclusivity.
- Preserve compact evidence provenance outside the operational instructions
  only when it materially supports future review.
- Select evidence proportional to the skill type using the authoring guidance.
  For hot promotion, material load-bearing changes, overlap, or costly loaders,
  compare representative work with and without the candidate: quality, errors,
  turns, calls, loaded context, and side effects. Do not require behavioral A/B
  testing for a simple reference or equate obedience with improvement.
- Run the exact skill validator and generated-catalog parity check. Review prose
  and semantic quality using current writing guidance. Report unmeasured lift
  honestly; structural validity alone does not establish usefulness.

Outside the universal-template repository, draft in the conversation unless the
user supplies an explicit destination.

## Report

    Evidence used:
    Qualification result:
    Material routed to code or gates:
    Skill created or changed:
    Visibility:
    Lift hypothesis and evidence (or unmeasured):
    Verification:
    Material deliberately omitted:

Request:

$ARGUMENTS
