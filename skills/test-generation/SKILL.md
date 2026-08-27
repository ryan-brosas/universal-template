---
name: test-generation
description: "Use when writing, expanding, or auditing tests; converting workflow rules into gates; or deciding what to test — the catch-first methodology (scarywood75 + Sewer56, Discord 7/19 + 8/3/26): a test is only good if it catches; pre-fix must fail and post-fix pass; narrow tests are anti-patterns; expand existing tests instead of adding duplicates; produce a test ledger the LLM maintains; turn multi-use scripts into workflows; every manual catch into a mechanical test; keep files small, group into cohorts; quantify the un-fixed vs fixed versions."
---

# Test Generation — catch-first, ledger-based

## Core Principle

A test is only good if it can **properly catch**. Pass means nothing; a suite is valuable only when the un-fixed version fails and the fixed version passes.

## When to Use / NOT

- **Use when:** writing a new test; a bug slipped through an *existing* test (expand, don't duplicate); auditing a suite for near-duplicates; converting project rules into gates; or told to "add tests".
- **NOT when:** the check is a smoke run with no failure mode you can state; OR you should be enforcing via a gate instead of a test (gates that "cannot be bypassed" > prompt-only rules).

## Workflow

1. **Determine what you want / gaps first** — a repo's popularity is not the proper judge; decide the *type* of bugs/gaps/issues that matter to you, then target that type.
2. **One broad test per failure-type**, not one per specific value. Target the class of bug — exposed functions not used elsewhere, non-existent consts, unused imports, near-identical dups (semantic distance scan).
3. **Test un-fixed AND fixed.** Pre-fix run must fail the test; post-fix run must pass. Record both.
4. **Maintain the test ledger.** The LLM keeps and updates a list of test names + what each targets; it checks the ledger every time something isn't caught, instead of inventing fixes.
5. **Never create duplicates or near-identical tests.** When a gap *should* have been caught and wasn't → **expand existing tests**, don't add new ones. Make tests for your test units too (shared functions, no static values/lists, no near-identical logic).
6. **Turn every manual catch into a mechanical test as much as possible.** Prompt the agent each turn to assess and check the workflow. Every time it jerry-rigs a script and uses it multiple times, turn that script into a **workflow/gate**. Where a script itself enforces order (e.g. CLI to verify file ordering), have the LLM call it — "AI is good at making you think it gave the proper results."
7. **Gate, don't prompt.** If the goal is that the agent must research, or must have used some tool — build a gate that cannot be bypassed (prompt-only instructions are inconsistent; a gate cannot be bypassed).
8. **Shape the repo to raise pass-rate**: keep files small; group changes into coherent themed cohorts (a larger problem broken into smaller themed tasks) — reduces turns the model has to think.
9. **Iterate forever.** The test suite evolves; never perfect. The babysitting is front-loaded — later you do much less.

## Red Flags

- A test suite full of pass = doing nothing; no red run recorded anywhere.
- Static values/lists in tests; near-identical duplicated tests; new orphans when a later catch was a variant.
- Prompting alone to force a tool to be used; the check is fluffy prose, not a mechanical gate.
- "Copy good repo code" as the selection criterion without gates (mixed results like asking a different coworker each day).

## Verification

- Every new or expanded test has both runs recorded: pre-fix run fails, post-fix run passes (Workflow step 3) — a suite with no red run recorded is doing nothing (Red Flags).
- The test ledger contains the test name + the failure-type it targets, and shows no near-duplicate entry (expand-don't-duplicate).
- Anything mechanical/deterministic was turned into a test or an unbypassable gate, not prompt-only prose (`references/mechanical-gates.md`).

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

- `references/test-ledger.md` — the ledger contract: every test = name + the failure-type it targets; check it every time something isn't caught; expand-don't-duplicate (scarywood75, 8/3/26)
- `references/mechanical-gates.md` — anything mechanical/deterministic → test or gate; quality packs (universal + per-language); unbypassable gate-over-prompt (scarywood75 + Tom, 7/19/26)
- `references/cohort-discipline.md` — keep files small, group changes into themed cohorts, convert repeated scripts into workflows and CLI gates (Sewer56)
