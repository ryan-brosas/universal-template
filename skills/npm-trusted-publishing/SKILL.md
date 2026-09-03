---
name: npm-trusted-publishing
description: "Use when setting up npm publishing from GitHub Actions for a package, adding a publish job or workflow, or answering 'how do I publish this to npm' — the AI does the publishing end to end in GitHub Actions (OIDC trusted publishing, no NPM_TOKEN secret) and guides the human through the one-time npmjs.com settings. Trigger-first; pick over secret-based publishing advice."
---

# npm Trusted Publishing from GitHub Actions

## Core Principle
Division of labor: the AI does **all** publishing work — workflows, gates, triggering the Actions run, triage, registry verification. The human's **only** job is the npmjs.com settings, and the AI walks them through it with exact field values. No stored token, ever.

## When to Use / NOT
- **Use when:** a repo's package should publish to npm from CI; adding an npm-publish job or workflow; the user asks for publishing "directly on npm" or without secrets.
- **NOT when:** publishing to private registries (no trusted publishing) or fully headless environments where no human can touch the npm website — say so explicitly.

## Workflow
1. **HARD-GATE — guide the registration first.** Before any publish run, give the human the exact trusted-publisher values and the docs link for current navigation (docs.npmjs.com/trusted-publishers):
   - repository: `<owner>/<repo>`
   - workflow file: the single publishing workflow (e.g. `npm-publish.yml`)
   - environment: empty
   One trusted publisher per package — consolidate every publish trigger into that one workflow file (`workflow_dispatch`), and trigger it directly (`gh workflow run`) from any other automation. Wait for the human to confirm the settings are saved. The same run can cut the GitHub Release: `gh release create v<version> ./dist/*.tgz --title … --generate-notes --latest` (`--prerelease` for hyphenated versions; skip if it exists) — note the gh flag is `--generate-notes`, not `--generate-release-notes` (that is the softprops action input name).
2. **Workflow shape:** `permissions: id-token: write`; `actions/setup-node` (v6) with `node-version: '24'` + `registry-url: 'https://registry.npmjs.org'` — OIDC publish needs npm ≥ 11.5.1 / Node ≥ 22.14, which the runner default npm does not guarantee; publish with `npm publish ./<dir>/*.tgz --provenance --access public`.
3. **Registry state:** `npm view <pkg>@<version>` — E404 means never published; an existing version is immutable and must never be republished.
4. **Trigger and own the run:** the AI dispatches the publish workflow (`gh workflow run`), watches to a conclusion, and triages failures — never hands CI work back to the human.
5. **Failure triage map:** see Red Flags.
6. **Duplicate-version guard before packing:** `npm view "<pkg>@$v" version` — if it resolves, fail with a message to bump; a `version` input (applied via `npm version X --no-git-tag-version`) never bypasses this.
7. **Stop condition:** YAML parses, no `NPM_TOKEN`/`NODE_AUTH_TOKEN` strings remain, project gates pass, human confirmed the npmjs.com settings; the live publish is only verifiable in Actions.

## Red Flags
- **HARD-GATE:** do not create `NPM_TOKEN`/`NODE_AUTH_TOKEN` secrets, `.npmrc` auth-token files, or token-guard steps for npm on GitHub Actions — legacy pattern; trusted publishing replaces it.
- **HARD-GATE:** pass tarballs with a `./`-prefixed path. A bare relative path (`dist/x.tgz`) is misparsed by npm 11 as a git spec → `exit 128: git ls-remote ssh://git@github.com/<path>.git` — nothing to do with auth.
- Never push CI work onto the human: registration guidance is the handoff, not the publish itself. Never claim npmjs.com UI paths from memory — give field values + the docs link.
- `ENEEDAUTH` in Actions = the runner npm lacks OIDC publish support — add the `setup-node` step, never a token.
- **HARD-GATE:** do not publish via a reusable-workflow call (`workflow_call` from another workflow) — GitHub's OIDC token then names the *calling* workflow file, which npm's one-publisher registration cannot match: `404 ... no permission` even though the dispatch path succeeds. Keep the publish in one workflow and trigger it with `gh workflow run`.
- Never publish the same version twice; never publish un-bumped per-push builds. Do not skip `--provenance`.

## Verification
- Human confirms the npmjs.com trusted-publisher settings are saved before the first Actions publish run.
- `grep -rn 'NPM_TOKEN\|NODE_AUTH_TOKEN' --exclude-dir=node_modules .` → only documentation stating none exist.
- YAML parse every touched workflow. Reproduce spec-resolution failures locally with `npm publish --dry-run` before another Actions run.
- Project's own gates pass before the pack step exists in CI.

## References
- https://docs.npmjs.com/trusted-publishers — registration fields, one-publisher limit.
- https://docs.npmjs.com/generating-provenance-statements — provenance claims, first-publish flags.
