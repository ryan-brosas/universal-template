# AI-assisted coding

## Treat generated code like a junior PR

- Review every diff: logic, security, scope, duplication, missing tests.
- Never commit credentials, `.env` contents, or copied secrets — `repo-hygiene.py` and project secret scans are backstops, not excuses to skip review.

## Prompt and slice discipline

- One slice at a time — do not "implement the whole app" in one pass (`leverage-playbook`: code is ground truth, stack skills).
- Give context pointers (files, skills, graph hits) and let the agent retrieve; do not hand-script every step.
- Maintain project spine: `AGENTS.md`, `.pi/state.md` — context files beat repeating rules in chat.

## Verification over self-report

- **HARD-GATE:** "I checked" without command output is a fail. Run the project gate and paste exit codes (`agent-code-quality-gate`, `verification-before-completion`).
- Feed gate failures back to the model; unbypassable checks beat re-prompting (`essentials/enforce-code-quality-mechanically.md`).

## Scope and duplication

- AI defaults to copy-paste helpers and drive-by refactors — run the five-check gate: scope, duplication, behavior tests, evidence, regressions.
- Bloat review mode in `code-review-and-quality` for large generated diffs.

## When to encode a lesson

- Repeated AI failure → mechanical check via `practices-to-ci`, not a new paragraph in AGENTS.md.
- One-off mistake → note in PR, fix the code, add regression test if reusable.

## Leaf skills

- `agent-code-quality-gate`, `code-review-and-quality`, `practices-to-ci`, `push-pr`, `leverage-playbook`
