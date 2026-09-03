# Learn from one approved source

Investigate one named uncertainty that matters to the active project. Source and
tests establish truth; the result is a bounded evidence pass, not a knowledge
capture campaign.

## Method

1. Inspect the active project's relevant source, tests, and runtime boundary.
2. State the exact unanswered question.
3. Use one approved project-local reference or indexed external source when
   outside prior art can materially answer it. Verify its identity and revision
   still match the approval; if they drift, stop and report the mismatch.
4. Use direct search, AST-aware tools, Fovea, or Codebase Memory only to locate
   the relevant implementation and tests.
5. Confirm every material conclusion in exact source and direct tests.
6. Compare the reference boundary with the active project's requirements,
   ownership, lifecycle, failure modes, and verification.
7. Recommend exactly one disposition: ADOPT, ADAPT, or OMIT.
8. Stop when the named uncertainty is resolved or the available evidence cannot
   resolve it.

## Output

    Question:
    Active-project evidence:
    Reference and revision:
    Exact source/test evidence:
    Relevant similarity:
    Important differences:
    Coverage or execution caveats:
    Disposition:
    Reason:

## Rules

- One question and normally one reference per invocation.
- Do not clone, index, ingest, or re-index without explicit approval.
- Do not create or expand a Foundation merely because a repository was studied.
- Do not create a skill, memory, note, summary, or campaign record
  automatically.
- Keep ordinary findings in the conversation.
- Direct source and tests outrank structural maps and generated explanations.

Request:

$ARGUMENTS
