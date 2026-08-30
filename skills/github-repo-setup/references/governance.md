# GitHub Governance — verified gh mechanics

All commands below verified against gh 2.98.0 (2026-08-21). Re-verify with `gh <cmd> --help` when behavior matters; do not trust memory over the installed CLI.

## Verified command inventory

| Operation | Command | Notes |
|---|---|---|
| auth / identity | `gh auth status` | record the authenticated account before mutating |
| repo existence | `gh repo view` (in repo root) | non-zero exit = absent or unauthenticated |
| create | `gh repo create OWNER/NAME --public\|--private\|--internal -d "desc"` | `-l/--license` exists; policy forbids choosing one for the user |
| description / topics | `gh repo edit -d "..." --add-topic a --add-topic b` / `--remove-topic` | |
| merge settings | `gh repo edit --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge --allow-update-branch --squash-merge-commit-message pr-title` | |
| template repo | `gh repo edit --template` / `gh repo create --template <repo>` | only when a template-repo purpose is confirmed |
| read settings | `gh repo view --json ...` | FIXED field allowlist — merge flags are NOT fields; use `gh api repos/OWNER/REPO --jq '.allow_squash_merge, .allow_merge_commit, .allow_rebase_merge, .delete_branch_on_merge'` |
| labels | `gh label list \| create \| edit \| delete` | `create --force` = idempotent upsert |
| rulesets | `gh api repos/OWNER/REPO/rulesets` | GET list, GET one, `-X POST --input file.json` |
| check names | `gh pr checks <n>` | the displayed check names are exactly what required-status-checks must match — not the YAML job ids |
| workflows | `gh api repos/OWNER/REPO/actions/workflows` | discovery of real CI |

## Preflight

```bash
gh --version && gh auth status   # capability + identity
git remote -v                    # HARD-GATE: stop on an unrelated origin
gh repo view 2>&1                # repository existence from the repo root
```

## Ruleset — default branch

Solo baseline example (`ruleset.json`), applied and then read back:

```json
{
  "name": "default-branch-protection",
  "target": "branch",
  "enforcement": "active",
  "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}},
  "bypass_actors": [],
  "rules": [
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {"type": "required_status_checks", "parameters": {
      "strict_required_status_checks_policy": false,
      "required_status_checks": [{"context": "<exact name from gh pr checks>", "integration_id": 15368}]
    }},
    {"type": "pull_request", "parameters": {
      "required_approving_review_count": 0,
      "dismiss_stale_reviews_on_push": false,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false,
      "allowed_merge_methods": ["squash"]
    }}
  ]
}
```

`integration_id: 15368` is the GitHub Actions app. For team repositories raise `required_approving_review_count` to 1+, set `required_review_thread_resolution: true`, and add CODEOWNERS-driven review only where ownership is real.

Reconcile, do not blindly create. A POST always creates a new ruleset — repeated setup would stack duplicate protections instead of reaching the idempotent no-op. Always reconcile:

```bash
# 1. List and find the matching ruleset (by name and target)
gh api repos/OWNER/REPO/rulesets --jq '.[] | {id, name, enforcement, rules: [.rules[].type]}'

# 2a. Intended config already present and identical -> skip the write (report "No changes required")
# 2b. A ruleset with the intended name exists but differs -> update it by id
gh api -X PUT repos/OWNER/REPO/rulesets/<id> --input ruleset.json
# 2c. None exists -> create
gh api -X POST repos/OWNER/REPO/rulesets --input ruleset.json

# 3. Read back and verify (every path) — HARD-GATE
gh api repos/OWNER/REPO/rulesets/<id>   # verify conditions, rules, bypass_actors
```

Preserve unrelated rulesets: inspect and touch only the one this skill manages. Prefer one ruleset over stacked legacy branch protection; migrate existing protection only deliberately, never silently.

## Required status checks

1. Local discovery: `.github/workflows/*` job definitions + `gh api repos/OWNER/REPO/actions/workflows`.
2. Authoritative names: open one PR and read `gh pr checks` — require exactly those strings.
3. No CI yet: scaffold via the `github-ci-workflow` skill (shape from `~/.agents/templates/github-pr-ci.yml`) when clearly in scope; otherwise report that required checks cannot be configured. Never invent a green status name.

## Merge policy

Inspect current settings and history first (`gh api repos/OWNER/REPO` + `git log --merges`). One understandable default wins: squash for most repositories (PR = one coherent change), preserving intentional merge-commit or rebase workflows. `--squash-merge-commit-message pr-title` keeps titles meaningful.

## Releases and tags

- Tags are release/version markers, separate from topics and labels. Only for versioned projects: `vMAJOR.MINOR.PATCH`; prereleases `v1.2.0-alpha.1` / `v1.2.0-beta.1` / `v1.2.0-rc.1`. Never a tag per PR.
- Audit existing release flows before adding anything; no release automation without a release concept.
- Notes: group by Added / Changed / Fixed / Performance / Breaking Changes / Migration; user-impact summaries with linked PRs and issues, not raw commit dumps.
- Semver decisions and changelog mechanics live in `git-workflow-and-versioning`.

## SECURITY, CODEOWNERS, dependency automation

- `SECURITY.md`: for public projects where private vulnerability reporting matters. Point at GitHub's private reporting or a real contact; never invent an email address — if no destination exists, report that the maintainer must configure one. Never direct reporters to open public issues with exploit details.
- `CODEOWNERS`: only when ownership is real (teams, specialized maintainers, sensitive or generated paths). `* @owner` in a solo repository is fake governance — skip it.
- Dependabot (or equivalent): only when it reduces noise — group related updates, cap frequency, declare ecosystems accurately. Omit for experiments and unversioned projects.

## Destructive-change guardrails

Visibility, ownership, default branch, deletion settings, archived state, and removal of existing rules are externally consequential. Preserve intentional values; additive configuration may proceed under a setup request; destructive or ambiguous changes surface to the user before execution.
