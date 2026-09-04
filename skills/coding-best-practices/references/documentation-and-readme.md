# Documentation and README

## README (project root)

Use `~/.agents/templates/readme.md` when bootstrapping via `project-bootstrap`. A reader should learn:

- What the project does and who it is for
- How to install/run/test (exact commands)
- Layout of important directories
- Where AGENTS.md / contribution rules live

Update README **after** behavior works — documents describe what IS, not promises.

## Docstrings and API docs

- Public functions/classes: parameters, return shape, errors thrown or `Result` tags — enough for a first-time caller without reading the body.
- Keep docstrings in sync with types; in typed languages prefer types as the contract and docstrings for semantics.

## Inline comments

- Same rule as naming reference: **why**, not restated **what**.
- Link to ADRs or issues when a decision looks arbitrary.

## Anti-slop

- No README that only restates the repo name.
- No docstring that duplicates the function name (`"""Gets the user."""`).
- No architecture essay in README when `AGENTS.md` (+ a project-context file, if the repo keeps one) already own the spine — link instead.

## Mechanical gates

- Template catalog: model review for relevance and prose; `repo-hygiene.py` only for exact publication contracts.
- Projects: spellcheck/codespell in CI optional; required only when it caught real issues before.

## Leaf skills

- Init/render templates: `project-bootstrap` (templates applied selectively)
- Review doc bloat: `code-review-and-quality` (bloat review mode)
