# GitHub governance

Use [GitHub CLI](../../github-cli/README.md) for authentication, command-specific
targeting, request construction and pagination. Complete the parent playbook's
preflight before writes. Examples below use an explicitly resolved `HOST` and
`OWNER/REPO`; they do not authorize changes or establish that a repository exists.

For repository settings, `gh repo edit OWNER/REPO` takes a positional target.
Read merge settings through `gh api --hostname HOST repos/OWNER/REPO`, not guessed
`gh repo view --json` fields. Labels have their own [reconciliation procedure](labels.md).
Select only the settings the project needs and check the installed command help.

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

`integration_id: 15368` is the GitHub Actions example, not a universal check
provider. Use the app ID observed on the intended check; names alone do not
establish provider identity. For team repositories raise `required_approving_review_count` to 1+, set `required_review_thread_resolution: true`, and add CODEOWNERS-driven review only where ownership is real.

`require_extra_approval_for_unattributed_changes` is the public-preview rule *Additional approval for unattributed Copilot pull requests*: it is enabled by default and adds one approval only when Copilot opens a PR under its own app identity instead of on behalf of a person. It does not add a requirement for a human author's own PR, so it is not a reason to expect a merge refusal, nor to raise the solo baseline's zero approvals (see `push-pr` for a post-push merge refusal that was first misattributed to this rule).

Reconcile, do not blindly create. A POST always creates a new ruleset — repeated setup would stack duplicate protections instead of reaching the idempotent no-op. Always reconcile:

```bash
# 1. Enumerate summaries; the list response does not include rules.
gh api --hostname HOST repos/OWNER/REPO/rulesets --paginate \
  --jq '.[] | {id, name, target, source, source_type, enforcement}'

# 2. Read the matching ruleset's full configuration before comparing.
gh api --hostname HOST repos/OWNER/REPO/rulesets/ID

# 3a. Intended config already present and identical -> skip the write.
# 3b. An owned ruleset differs and updating it is authorized -> update by ID.
gh api --hostname HOST -X PUT repos/OWNER/REPO/rulesets/ID --input ruleset.json
# 3c. None exists and creation is authorized -> create.
gh api --hostname HOST -X POST repos/OWNER/REPO/rulesets --input ruleset.json

# 4. Read back the updated/returned ID; verify conditions, rules and bypass actors.
gh api --hostname HOST repos/OWNER/REPO/rulesets/ID
```

List summaries are not enough to compare rules or bypass actors. Inspect each
relevant detail response, including its source; inherited organization rules are
not repository-owned settings. After an ambiguous write failure, read state
before retrying a POST that might already have created the ruleset.

Preserve unrelated rulesets: inspect and touch only the one this skill manages. Prefer one ruleset over stacked legacy branch protection; migrate existing protection only deliberately, never silently.

## Required status checks

Use the [CI handoff](../../github-actions-engineering/references/required-checks.md):
read existing workflows and a real run/PR on the intended repository and revision,
then configure the observed check contexts and providers. `gh pr checks` does not
include provider identity; use check-run API data when that matters. Do not create
a PR merely to discover names during an audit. If no run exists, report the
unverified contract or arrange a run only within the requested scope. With no CI,
scaffold through `github-actions-engineering` only when authorized; never invent
a green status name.

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
