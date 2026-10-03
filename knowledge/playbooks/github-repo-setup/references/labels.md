# Label Taxonomy — namespaced, sized to the project, idempotent

## Dimensions

| Dimension | Labels | Rule |
|---|---|---|
| `type:` | `type:bug`, `type:feature`, `type:refactor`, `type:docs`, `type:test`, `type:chore`, `type:performance`, `type:ci`, `type:build`, `type:security`, `type:dependencies` | create only the relevant ones; on PRs these come from the title via one owning component (for example, a PR-title parser) |
| `area:` | `area:frontend`, `area:backend`, `area:api`, `area:cli`, `area:runtime`, `area:ci`, `area:docs`, ... | inferred from real top-level paths only — never fake areas |
| `priority:` | `priority:p0` (critical) … `priority:p3` (low) | only when the project actually prioritizes issues |
| special | `breaking-change`, `release:skip`, `blocked`, `needs-reproduction`, `good-first-issue`, `help wanted` | only what a workflow consumes; `breaking-change` and the `type:*` set drive `.github/release.yml` categories |

Organization repositories: if GitHub Issue Types exist for issues, use them for issue classification and keep `type:*` as the PR taxonomy; do not maintain the same classification twice. Detect at runtime (`gh api orgs/ORG/issue-types` when applicable). |

Avoid giant catalogs. A tiny CLI may need four labels; that is correct.

## Suggested colors

| Label | Color | | Label | Color |
|---|---|---|---|---|
| type:bug | `d73a4a` | | priority:p0 | `b60205` |
| type:feature | `1d76db` | | priority:p1 | `d93f0b` |
| type:refactor | `fbca04` | | priority:p2 | `fbca04` |
| type:docs | `0075ca` | | priority:p3 | `cccccc` |
| type:test | `0e8a16` | | area:* | `bfd4f2` |
| type:chore | `fef2c0` | | breaking-change | `d93f0b` |
| type:security | `b60205` | | blocked | `5319e7` |
| type:dependencies | `0366d6` | | needs-reproduction | `ededed` |

`gh label create` picks a random color when omitted — the exact hex is not load-bearing.

## Idempotent reconciliation

Use [GitHub CLI](../../github-cli/README.md) for targeting and API mechanics.
Inspect the complete collection before comparing it with the requested taxonomy:

```sh
gh api --hostname HOST repos/OWNER/REPO/labels --paginate \
  --jq '.[] | {name, color, description}'
```

An unsuccessful or incomplete read is not an empty label set. A fixed
`gh label list --limit` is only a bound; do not hide read errors with `|| true`
or process substitution before deciding what to create. Compare names, colors
and descriptions, preserving intentional labels and skipping unchanged entries.

For an authorized difference, `--force` creates a missing label or updates an
existing one's color and description; it does not itself avoid an unchanged write.
For example, when the requested taxonomy includes this label:

```sh
gh label create 'type:bug' --repo HOST/OWNER/REPO --color d73a4a \
  --description 'Something is broken' --force
```

Read back the complete collection and compare the affected labels. A partial
failure needs inspection before retrying; do not apply a generic catalog blindly.

## Default-label reconciliation

- GitHub defaults (`bug`, `enhancement`, `documentation`, `question`, ...) may stay; do not churn a working set.
- Before retiring a default superseded by a namespaced label, check references: `gh issue list --repo HOST/OWNER/REPO --state open --label <name>` and `gh pr list --repo HOST/OWNER/REPO --state open --label <name>`. Retire only when both are empty.
- HARD-GATE: never delete a label carrying open issues or PRs without migrating those references first.

## Optional automation

- `.github/labeler.yml` + the actions/labeler workflow when project paths map deterministically to `area:` labels (`src/web/** → area:frontend`, `.github/** → area:ci`, `docs/** → area:docs`). Prefer deterministic path mapping over label inference from prose.
- `size:S/M/L/XL` labels are informational only — never a merge blocker; omit when they add nothing (generated diffs and necessary refactors exist).
