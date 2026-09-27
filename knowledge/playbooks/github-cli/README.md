---
title: github-cli
summary: "Use when choosing or scripting GitHub CLI commands, diagnosing gh authentication, extracting structured GitHub data, or making REST/GraphQL requests; covers shared command mechanics without replacing delivery policy."
kind: playbook
---

# GitHub CLI

Use `gh`'s domain commands for ordinary repository, issue, PR, run and release
operations; use `gh api` when those commands lack a required field or operation.
Check `gh --version` and the selected command's `--help` before relying on a flag.
The [official manual](https://cli.github.com/manual/) is the reference, not a
command catalog to copy into instructions. Installed help can differ from the site.

## Establish identity and target

- Check the active account on the intended host with
  `gh auth status --active --hostname <host>`. **Do not use the exit status of
  `gh auth status --json hosts` as an auth gate:** it is zero even for reported
  authentication problems unless a fatal error occurs. Auth success also does
  not prove permission for the requested resource.
- Environment credentials override stored credentials: `GH_TOKEN` precedes
  `GITHUB_TOKEN`; Enterprise Server uses `GH_ENTERPRISE_TOKEN` before
  `GITHUB_ENTERPRISE_TOKEN`. Diagnose whether overrides are set without printing
  values. Never use `--show-token` in evidence; avoid HTTP debug logs containing
  sensitive request data. Changing accounts or scopes is not a routine retry.
- Use the [target guard](../gh-repo-target-guard/README.md) for repository intent
  and fork ambiguity. Prefer explicit repository arguments or `--repo
  [HOST/]OWNER/REPO` where supported. `gh api` instead takes an explicit endpoint
  and `--hostname`; it has no `--repo` flag.
- For unattended calls, scope `GH_PROMPT_DISABLED=1` and `GH_PAGER=cat` to the
  invocation and supply required arguments. Disabling prompts is not permission
  to accept defaults, log in, push or fork.

## Read structured, bounded evidence

Request only needed `--json` fields and filter with built-in `--jq`; no separate
jq installation is needed for that flag. Run a command with bare `--json` to
list supported fields. Do not parse human tables.

```sh
gh repo view OWNER/REPO --json nameWithOwner,url,defaultBranchRef
gh pr view NUMBER --repo OWNER/REPO --json url,state,headRefOid,baseRefName
gh run view RUN_ID --repo OWNER/REPO --json status,conclusion,headSha,url
```

A list limit is a bound, not proof of completeness. Filter to the relevant
repository, branch, state, event or revision first. For exhaustive API reads,
follow [API request and pagination mechanics](references/api.md). Keep exact IDs,
SHAs and URLs; a successful request with an empty list proves no more than that
query's scope.

## Leave workflow decisions with their owners

- [Push/PR/review](../push-pr/README.md): authorization, body files, explicit head
  and base, duplicate prevention, and read-back after writes. `gh pr create
  --dry-run` can still push; it is not a read-only probe. After a write error,
  inspect remote state before retrying: a nonzero exit does not prove rollback
  (for example, a PR can be created despite a failed attachment upload).
- [CI observation](../push-pr/references/ci-and-observation.md): revision-bound
  checks, command-specific exit codes, bounded watching and failure logs.
- [Repository setup](../github-repo-setup/README.md) and
  [shipping](../ship-pr/README.md): governance and merge policy, not implicit
  permission from CLI capability.

Report the target, observed result and remaining gap. Re-read changed remote
state before claiming success. Do not retry a mutation just to obtain prettier
output.

## Sources

- [Authentication status](https://cli.github.com/manual/gh_auth_status)
- [Environment](https://cli.github.com/manual/gh_help_environment)
- [JSON formatting](https://cli.github.com/manual/gh_help_formatting)
- [Exit codes](https://cli.github.com/manual/gh_help_exit-codes)
- [PR creation](https://cli.github.com/manual/gh_pr_create)
