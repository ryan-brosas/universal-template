---
name: quality-gate-methodology
description: "Use when writing or reviewing tests and quality gates for code — a test is only good if it catches: test un-fixed + fixed, broad tests, expand don't duplicate, maintain a test list, turn manual catches into workflows."
disable-model-invocation: true
---

# Quality Gate Methodology

The mechanical-enforcement discipline from Pillar 4, made concrete. A test is
only a good test if it can properly CATCH — a passing test means nothing.

## Core Principle

A test is only a good test if it can properly CATCH. Test the un-fixed AND fixed
versions (pre-fix FAIL, post-fix PASS), target the TYPE of bug rather than one
instance, expand existing tests instead of duplicating them, keep a test list, and turn
every manual catch into a mechanical test.

## Iron Laws

<EXTREMELY-IMPORTANT>
- **A test is only good if it catches.** You must test the un-fixed AND fixed
  versions: pre-fix should FAIL the test, post-fix should PASS. Otherwise the
  test proves nothing.
- **Broad tests, not many.** Target the TYPE of bug/gap/issue, not specific
  things. A test that only catches one case is weak.
- **Expand, don't duplicate.** When something should've been caught but wasn't,
  EXPAND the existing test rather than creating a new near-identical one.
- **Maintain a test list.** Keep a list of tests and what they target; check it
  every time something isn't caught.
- **Turn manual catches into mechanical tests.** Every manual catch becomes a
  test. Every jerry-rigged script reused more than once becomes a workflow.
</EXTREMELY-IMPORTANT>

## When to Use

When writing new tests, reviewing tests, or adding quality gates to code.
Also when you catch a bug that existing tests missed — that's a signal to
expand the test, not just fix the bug.

## Workflow

Test un-fixed + fixed → write broad tests targeting the bug type → expand, don't
duplicate → maintain the test list → test your test units → turn manual catches into
workflows. The full steps are in `The Methodology` below.

## The Methodology

1. **Test un-fixed + fixed.** Write the test so it FAILS against the broken
   code and PASSES against the fixed code. This proves it catches.
2. **Write broad tests.** Ask "what TYPE of bug does this catch?" — make the
   test catch the class, not one instance.
3. **Expand, don't duplicate.** When a bug slips past existing tests, expand
   the relevant test to cover it. Avoid creating duplicate/near-identical tests.
4. **Maintain a test list.** Track each test + what it targets. When something
   isn't caught, consult the list and expand the right test.
5. **Test your test units.** Ensure tests are well-formed: use shared
   functions, avoid static values/lists, avoid near-identical logic.
6. **Turn manual catches into workflows.** Every time a manual check or
   jerry-rigged script is reused, convert it into a workflow/CI gate.

## Judging "good" code

- Do NOT judge code quality by repo stars or "it works." You need mechanical
  tests and gates — otherwise you get mixed results, like asking a different
  coworker every day if someone does good work.
- Determine what YOU want/like/gaps yourself, then turn that into tests.

## Structural practices

- Keep files small; group changes into themed cohorts (improves pass rate,
  makes models think less).
- Turn as much as possible into code: a CLI tool that verifies beats prompting
  the LLM to do it.

## Red Flags

- A test that passes on both the broken and the fixed code — it proves nothing.
- A test that only catches one specific case instead of the type of bug.
- Creating a new near-identical test when an existing one should have been expanded.
- No test list to consult when something isn't caught.
- A jerry-rigged script reused more than once that never became a workflow.
- Judging code quality by repo stars or "it works" instead of mechanical tests and
  gates.

## Verification

- Every test fails on the broken version and passes on the fixed version.
- No duplicate/near-identical tests.
- A test list exists and is consulted when something isn't caught.
- Manual catches have been converted to mechanical tests/workflows.

## Skill Result Contract

```
<skill_result>
  <skill><name></skill>
  <status>success|partial|blocked|failure</status>
  <evidence>…</evidence>
  <artifacts>…</artifacts>
  <risks>…</risks>
</skill_result>
```

## References

N/A — no reference files; the methodology is fully specified in this file.
