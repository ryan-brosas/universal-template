# AI-assisted coding

## Treat generated code like a junior PR

- Review every diff: logic, security, scope, duplication, missing tests.
- Never commit credentials, `.env` contents, or copied secrets — `repo-hygiene.py` and project secret scans are backstops, not excuses to skip review.

## Prompt and scope discipline

- Scope the task clearly — agree on outcome and boundaries before large diffs; code is ground truth, captured skills stack leverage.
- Give context pointers (files, skills, graph hits) and let the agent retrieve; do not hand-script every step.
- Prefer current source, Git, the tracker, and relevant session evidence. If durable recovery or coordination state may be needed, explicitly load `../../goal-setup/SKILL.md` to qualify it; duration alone does not earn a record.

## Verification over self-report

- **HARD-GATE:** "I checked" without command output is a fail. Run the project gate and paste exit codes (`agent-code-quality-gate`; the global AGENTS.md finish line owns the rule).

Evidence hierarchy (what backs each claim):

| Claim | Required evidence |
|---|---|
| "Test passes" | Test runner output, exit 0 |
| "Typecheck clean" | `tsc --noEmit`, exit 0 |
| "Lint clean" | Linter output, exit 0 |
| "Build succeeds" | Build output, exit 0 |
| "Behavior is X" | Repro + observed output |
| "Code matches spec" | Diff or path + line range |
| "Bug is fixed" | Regression test fails without, passes with |
| "Shipped" | All of the above + commit / PR link |

- Feed gate failures back to the model; unbypassable checks from `practices-to-ci` beat re-prompting.

## Scope and duplication

- AI defaults to copy-paste helpers and drive-by refactors — run the five-check gate: scope, duplication, behavior tests, evidence, regressions.
- Bloat review mode in `code-review-and-quality` for large generated diffs.

## When to encode a lesson

- Repeated AI failure → mechanical check via `practices-to-ci`, not a new paragraph in AGENTS.md.
- One-off mistake → note in PR, fix the code, add regression test if reusable.

## Leaf skills

- `agent-code-quality-gate`, `code-review-and-quality`, `practices-to-ci`, `push-pr`
