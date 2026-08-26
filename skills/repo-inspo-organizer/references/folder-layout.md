# Inspiration folder layout

Use the existing inspiration library resolved from /home/utopia/work/inspo.
Do not infer a new root from a template or create a second literal inspo folder.

## Ownership

| Item | Location | Rule |
|---|---|---|
| inspiration checkout | existing work/inspo/<slug>/ | read-mostly pinned Git checkout |
| source sidecar | beside checkout as <slug>.source.yml | records physical identity and provenance |
| optional work record | <slug>-work/ | organization facts only |
| optional study record | <slug>-study/ | preserve if already present; this skill does not create or fill it |
| catalog | INSPO.md, QUEUE.md | scoped path/status pointers only |

## Placement rules

1. Resolve the absolute root with pwd and readlink -f before writing.
2. Reuse the existing flat or nested library shape; never migrate automatically.
3. Never create a Git worktree for an inspiration checkout.
4. Never place an inspiration checkout beside an active project to avoid the library.
5. Never create a duplicate checkout or second alias root because a template uses a
different spelling.
6. Verify the checkout path, remote, ref, HEAD, and is_worktree=false before closing.

Graph indexing, repository learning, tests, DSH implementation, and foundation-skill
promotion are separate operations and do not belong in this layout reference.
