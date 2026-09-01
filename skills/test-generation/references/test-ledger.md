# Test Ledger Protocol

Source: scarywood75, 2026-08-03; distilled from the original discussion transcript.

## Why a ledger

Without a ledger, an LLM will "prompt" its way to dozens of duplicate / near-identical tests as edge cases accrue. The ledger is the memory of intent: what each test **targets**, so each new gap is routed to the test that should have caught it.

## The protocol

1. Each test has a row: `name` · `targets (the TYPE of bug/gap/issue, not a specific value)` · `how to reproduce a red run`.
2. Each time something slips through, first consult the ledger: "which existing test *should* have caught this?" — if it exists, **expand it**; only if nothing targets it do you add a new test, and you add it to the ledger.
3. Never create a near-identical twin. Before adding, diff against the ledger semantically (shared functions; different static value = duplicate).
4. The LLM checks the ledger every time a gap is reported, and can update the ledger rows when intent shifts.

## Red-run discipline

- A test is proven by its **red run**: run the code BEFORE the fix → the test fails; apply fix → test passes.
- Log both runs in the PR/change notes (e.g. `RED: X fails, GREEN: X passes`).
- Gates enforce the ledger too: no empty test bodies, no static-assert-only tests (no assertions on fixed literals).

## The moving target caveat

"It's never going to be perfect." The ledger keeps the suite *tight and legible* as it evolves, which is what keeps babysitting cheap later.
