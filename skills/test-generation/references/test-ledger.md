# Optional test ledger

Source: scarywood75, 2026-08-03; distilled from the original discussion
transcript and qualified for proportional use.

## When a ledger helps

A lightweight ledger can make intent visible during a broad test audit, a
multi-test migration, or work on a suite with recurring near-duplicates. Do not
create or maintain one for a small suite when names and nearby source already
make ownership obvious.

## Minimal shape

Record only what improves a coverage decision:

```text
test name | failure class or invariant | reproducible RED command, if available
```

When a defect escapes, ask which existing test owns that failure class. Expand
it when the ownership is clear. Add a new test when the boundary, responsibility,
or isolation need is genuinely different.

## Evidence

For a safely reproducible regression, record the failing pre-fix result and the
passing post-fix result in the change evidence. If the pre-fix state is
unavailable or unsafe to run, retain the strongest direct failure evidence and
state that limitation. Do not fabricate RED or require fixed-literal bans that
would reject legitimate contract tests.
