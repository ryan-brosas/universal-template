---
name: javascript-project-practices
description: "Use when bootstrapping or reviewing JavaScript/Node projects, elsewhen git/PR workflow, README template, env config, lockfiles, feature folders, ESLint/Prettier, REST API conventions, and lighthouse/axe from day one."
invocation: manual
disable-model-invocation: true
---

# JavaScript Project Practices

Application skill for elsewhencode/project-guidelines ingest (`awesome-guidelines`). Line-level JS: `javascript-coding-practices`, `node-coding-practices`. Git detail: `git-workflow-and-versioning`. REST depth: `api-design-practices`. WCAG depth: `wcag-accessibility-practices`.

## Core Principle

Maintainable JS projects combine **feature-branch discipline**, **env-driven config**, **feature-folder structure**, **mechanical lint/test gates**, and **REST + a11y conventions from day one**, not bolted on after launch.

## When to Use / NOT

- New Node/React/Vue/Angular repo setup or major restructure.
- Auditing JS monolith layout, package.json, CI, README, API surface.
- Onboarding checklist for elsewhen-style projects.

**NOT when:**

- Single-file script, minimal `node-coding-practices` only.
- Non-JS stack, use language-specific practice skill.
- Deep WCAG audit only, `wcag-accessibility-practices` primary.

## Workflow

1. **Git/docs**, branches, commits, README (`js-project-git-docs.md`).
2. **Env/deps/test**, secrets, lockfile, colocated tests (`js-project-env-deps-test.md`).
3. **Structure/style**, folders, ESLint, logging (`js-project-structure-style.md`).
4. **API/a11y/verify**, REST, security, axe/lighthouse (`js-project-api-a11y-verify.md`).

## Red Flags

- Direct push to develop/master
- Secrets or tokens in committed source
- Missing package-lock.json (or yarn.lock)
- controllers/models folder split on small app
- Per-environment config file proliferation
- Committed build/dist output
- eslint-disable left in PR
- Large commented-out code blocks
- console.log in production client bundle
- REST URLs with verbs (`/getUsers`)
- Database table names exposed in API paths
- Auth token in query string
- HTTP-served API in production
- No README sections from sample template
- UI project with zero a11y lint or audit setup
- Skipping local test/lint before PR

## Verification

- Branch protection + required CI (lint, test)
- `.env.example` without secrets; env validation at boot
- Lockfile committed; npm audit clean or documented exceptions
- Feature-folder tree; build gitignored
- README matches sample sections for project type
- API README or OpenAPI for HTTP services
- lighthouse/axe or jsx-a11y in CI for UI projects


## References

- `awesome-guidelines/references/js-project-learning-note.md`
- `awesome-guidelines/references/js-project-git-docs.md`
- `awesome-guidelines/references/js-project-env-deps-test.md`
- `awesome-guidelines/references/js-project-structure-style.md`
- `awesome-guidelines/references/js-project-api-a11y-verify.md`

## Related skills

- `git-workflow-and-versioning`, commit/branch conventions
- `api-design-practices`, REST contract patterns
- `webappsec-coding-practices`, web security depth
- `wcag-accessibility-practices`, WCAG 2.1 AA
