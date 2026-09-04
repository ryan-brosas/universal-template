---
name: quality-gate-methodology
description: "Use when writing or reviewing tests and quality gates for code, a test is only good if it catches: pre-fix FAIL and post-fix PASS, broad tests over single cases, expand existing tests instead of duplicating, promote repeated manual catches into gates when the value is proven."
invocation: internal
disable-model-invocation: true
---

# Quality Gate Methodology

The mechanical-enforcement discipline from Pillar 4, made concrete. A test is
only a good test if it can properly CATCH, a passing test means nothing.

## Core Principle

A test is only a good test if it can properly CATCH. Test the un-fixed AND fixed
versions (pre-fix FAIL, post-fix PASS), target the TYPE of bug rather than one
instance, expand existing tests instead of duplicating them, keep a test list, and turn
every manual catch into a mechanical test.

## Core rules

<EXTREMELY-IMPORTANT>
- **A test is only good if it catches.** Test the un-fixed AND fixed versions:
 pre-fix should FAIL the test, post-fix should PASS. Otherwise the test proves
 nothing.
- **Broad tests, not many.** Target the TYPE of bug/gap/issue, not one
 instance. A test that only catches one case is weak.
- **Expand, don't duplicate.** When something should've been caught but wasn't,
 EXPAND the existing test rather than creating a near-identical one.
</EXTREMELY-IMPORTANT>

Supporting practices (apply where the value is real, not as ceremony): keep a
short test inventory when the suite is large enough to need one, and promote a
manual catch into a mechanical gate when it recurs or its escape cost is high
("repeated, proven value", not every catch, and not every reused script).

## When to Use

When writing new tests, reviewing tests, or adding quality gates to code.
Also when you catch a bug that existing tests missed, that's a signal to
expand the test, not just fix the bug.

## Workflow

Test un-fixed + fixed → write broad tests targeting the bug type → expand, don't
duplicate → test your test units → promote repeated manual catches into gates
when the value is proven. The full steps are in `The Methodology` below.

## The Methodology

1. **Test un-fixed + fixed.** Write the test so it FAILS against the broken
 code and PASSES against the fixed code. This proves it catches.
2. **Write broad tests.** Ask "what TYPE of bug does this catch?", make the
 test catch the class, not one instance.
3. **Expand, don't duplicate.** When a bug slips past existing tests, expand
 the relevant test to cover it. Avoid creating duplicate/near-identical tests.
4. **Keep a test inventory when it earns itself.** For a large suite, track
 each test + what it targets; when something isn't caught, consult it and
 expand the right test. Skip the ceremony on a small suite.
5. **Test your test units.** Ensure tests are well-formed: use shared
 functions, avoid static values/lists, avoid near-identical logic.
6. **Promote proven catches into gates.** When a manual check or jerry-rigged
 script keeps catching real escapes, convert it into a test/CI gate, value
 and false-positive cost decide, not reuse count alone.

## Judging "good" code

- Do NOT judge code quality by repo stars or "it works." You need mechanical
 tests and gates, otherwise you get mixed results, like asking a different
 coworker every day if someone does good work.
- Determine what YOU want/like/gaps yourself, then turn that into tests.

## Structural practices

- Keep files small; group changes into themed cohorts (improves pass rate,
 makes models think less).
- Turn as much as possible into code: a CLI tool that verifies beats prompting
 the LLM to do it.

## Red Flags

- A test that passes on both the broken and the fixed code, it proves nothing.
- A test that only catches one specific case instead of the type of bug.
- Creating a new near-identical test when an existing one should have been expanded.
- No test list to consult when something isn't caught.
- A repeatedly load-bearing manual check that never became a gate despite real
 escape risk.
- Judging code quality by repo stars or "it works" instead of mechanical tests and
 gates.

## Verification

- Every new test fails on the broken version and passes on the fixed version.
- No duplicate/near-identical tests.
- Test inventory (when kept) consulted when something isn't caught.
- Proven repeated catches promoted to gates; unproven ones left as manual
 checks with a note.


## References

N/A, no reference files; the methodology is fully specified in this file.
