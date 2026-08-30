# Account- and organization-level GitHub defaults

Generic community files can be configured once at the account or organization
level instead of per repository. Facts below are verified against docs.github.com
("Creating a default community health file", organization custom properties).

## What the account/org `.github` repository provides

Supported default community health files:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `SUPPORT.md`
- `CODE_OF_CONDUCT.md`
- `FUNDING.yml`
- `GOVERNANCE.md`
- issue templates (`.github/ISSUE_TEMPLATE/` plus `config.yml`)
- pull request templates
- discussion category forms (`.github/DISCUSSION_TEMPLATE/`)

Constraints that matter:

- Works for personal accounts and organizations.
- The `.github` repository must be public or internal. A private `.github`
  repository does not apply defaults, and issue and pull request templates
  additionally require a public `.github` repository.
- `LICENSE` is explicitly not supported as a default file. Licenses stay per
  repository.
- Placement: repository root, `.github/`, or `docs/` in the `.github` repo;
  issue templates must sit in `.github/ISSUE_TEMPLATE/`.

## Precedence

A repository-local file overrides the account/org default. Keep only truly
generic content in the account defaults; repository-specific verification
commands never move there. The generic wording is "run the repository's
documented verification", and individual repositories override with exact
commands.

## Organization-level future path

For organization repositories, current mechanisms extend the same composition
without rewriting skills:

1. repository classification (maturity class from `setup-matrix.md`)
2. custom properties (`POST /orgs/{org}/properties`, typed select properties)
3. organization rulesets
4. inherited governance across repositories

Do not build any of this for personal repositories. It is a documented upgrade
path, not current work.

## Boundary

Creating or mutating the account-level `.github` repository is broader than
configuring one repository. Report the opportunity and what it would contain;
create or change it only when the current task explicitly authorizes
account-level GitHub changes.
