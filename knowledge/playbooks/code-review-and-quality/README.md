---
title: code-review-and-quality
summary: Use when reviewing code, a PR or delegated work; investigate correctness and unnecessary complexity from requirements, source and runtime evidence, without a finding quota.
kind: playbook
---

# Code review and quality

Review whether the change solves the stated problem, preserves required behavior
and introduces avoidable complexity. A sound patch may need no changes. Do not
invent findings, deletions or simplifications to demonstrate that a review ran.

## Scope and evidence

1. Establish the requested behavior, review scope and applicable project
   constraints. Separate existing problems from changes introduced by the patch.
2. Trace affected execution paths, callers and tests. Read enough surrounding
   source to understand the contract; a diff alone may hide important uses.
3. Investigate correctness, failure handling, compatibility, security and other
   risks that apply. Use the project's actual conventions, not a universal
   language, framework or development-method checklist.
4. For suspected bloat, ask what would break if it were removed. Check public
   consumers, runtime registration, side effects and recovery behavior before
   calling something dead. A single caller does not by itself make an abstraction
   unnecessary, nor does repetition by itself justify a shared abstraction.
5. Exercise the affected behavior with focused existing tests or direct probes
   where practical. Inspect failures and revise the finding; do not treat a green
   command as proof that the relevant path ran.

A review request is not permission for unrelated rewrites. Keep out-of-scope
findings separate, with evidence and a reason to fix, defer or reject them.

## Report useful findings

For each finding, cite the source, explain the concrete consequence and recommend
the smallest appropriate fix. Distinguish a reproduced failure from a risk or
open question. Standard review may use `[blocker]`, `[should-fix]`, `[nit]` and
`[question]`; severity follows impact, not how strongly a rule is worded.

For a bloat-focused review, use `[delete]` or `[simplify]` only when supported by
consumer and behavior evidence. Use `[keep-with-reason]` for apparently redundant
code that protects a real requirement. Do not optimize for a shorter diff at the
expense of clarity, compatibility or reliability.

## Verification

Report the paths examined, checks actually run, observed results and remaining
coverage gaps. If no actionable findings remain, say so and identify the review's
limits. Neither a finding count nor an empty report establishes correctness;
the supporting investigation does.
