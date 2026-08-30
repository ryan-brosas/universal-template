# Label Taxonomy — namespaced, sized to the project, idempotent

## Dimensions

| Dimension | Labels | Rule |
|---|---|---|
| `type:` | `type:bug`, `type:feature`, `type:refactor`, `type:docs`, `type:test`, `type:chore`, `type:performance`, `type:security`, `type:dependencies` | create only the relevant ones |
| `area:` | `area:frontend`, `area:backend`, `area:api`, `area:cli`, `area:runtime`, `area:ci`, `area:docs`, ... | inferred from real top-level paths only — never fake areas |
| `priority:` | `priority:p0` (critical) … `priority:p3` (low) | only when the project actually prioritizes issues |
| special | `breaking-change`, `blocked`, `needs-reproduction`, `good-first-issue`, `help wanted` | only what a workflow consumes |

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

## Idempotent sync (verified on gh 2.98.0)

`gh label create <name> --force` creates missing labels and updates existing ones in one pass, so re-running is a no-op:

```bash
# inspect first (--limit: the default fetches only 30 labels)
diff <(cat <<'WANT'
type:bug
type:feature
area:ci
WANT
) <(gh label list --limit 1000 --json name --jq '.[].name' | sort) || true

# reconcile (adjust the set to the discovered project)
while IFS='|' read -r name color desc; do
  gh label create "$name" --color "$color" --description "$desc" --force
done <<'EOF'
type:bug|d73a4a|Something is broken
type:feature|1d76db|New capability
type:docs|0075ca|Documentation only
type:chore|fef2c0|Maintenance and tooling
area:ci|bfd4f2|CI, workflows, and repository governance
EOF
```

## Default-label reconciliation

- GitHub defaults (`bug`, `enhancement`, `documentation`, `question`, ...) may stay; do not churn a working set.
- Before retiring a default superseded by a namespaced label, check references: `gh issue list --state open --label <name>` and `gh pr list --state open --label <name>`. Retire only when both are empty.
- HARD-GATE: never delete a label carrying open issues or PRs without migrating those references first.

## Optional automation

- `.github/labeler.yml` + the actions/labeler workflow when project paths map deterministically to `area:` labels (`src/web/** → area:frontend`, `.github/** → area:ci`, `docs/** → area:docs`). Prefer deterministic path mapping over label inference from prose.
- `size:S/M/L/XL` labels are informational only — never a merge blocker; omit when they add nothing (generated diffs and necessary refactors exist).
