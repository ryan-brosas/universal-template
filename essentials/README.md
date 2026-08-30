# Essentials - rationale and decision references

Cold references, not always-loaded policy: read the smallest relevant file
when a policy decision needs explanation, and skip the rest. Six working
principles synthesized from the Discord threads in `discord-material/`
(verbatim source kept there; this directory keeps only what still guides
decisions today). `operating-philosophy.md` is the long-form rationale behind
the six; the other files carry one principle each. Nothing here is a hard
behavioral rule: enforcement lives in mechanical gates (principle 4), not in
prose.

## The six principles

| # | Principle | File | One line |
|---|---|---|---|
| 1 | **Code is ground truth** | `guiding-small-model.md` | Read the actual code, tests, and docs before believing any summary, including your own memory of them. |
| 2 | **Steer outcomes, not behavior** | `steer-outcomes-not-behavior.md` | Do not write behavioral rule lists; define the outcome and verify it with a mechanical gate. |
| 3 | **Stack your leverage** | `stack-your-leverage.md` | Keep representation assets that pay for themselves; promote them when they prove out; do not hoard. |
| 4 | **Enforce mechanically** | `enforce-code-quality-mechanically.md` | Anything deterministic becomes a gate (test, linter, AST check, CI), never a prompt plea. |
| 5 | **Catch-first tests** | `how-to-build-good-tests.md` | A test is only good if it can catch: RED on the bug, GREEN after the fix. |
| 6 | **Durable context memory** | `openviking-foundation.md` | Past experience is retrieved at runtime; machine facts are probed, never frozen into docs. |

Question-to-file routing:

- "Which source do I trust?" -> `guiding-small-model.md`
- "Rules or outcomes?" -> `steer-outcomes-not-behavior.md`
- "What is worth keeping?" -> `stack-your-leverage.md`
- "How do I enforce this?" -> `enforce-code-quality-mechanically.md`
- "What makes a test good?" -> `how-to-build-good-tests.md`
- "Where does durable memory live?" -> `openviking-foundation.md`
- "Why these six?" -> `operating-philosophy.md` (explanatory rationale)

Current work objectives live in `docs/roadmap.md`, not here.
`discord-material/` holds the verbatim threads these principles were
synthesized from; quote them when extending the philosophy, and keep
philosophy edits faithful to their source.

## Using this directory

- Read the principle relevant to the decision at hand; skip the rest.
- When a principle and reality conflict, fix the principle in the same change.
- Machine state (endpoints, corpus sizes, model catalogs, auth state) is
  never recorded here; probe it at runtime.
