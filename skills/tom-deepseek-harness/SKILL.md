---
x-manual-only: true
name: tom-deepseek-harness
description: "Use when working on Tom's DeepSeek Harness source checkout: update from Tom's remote, edit safely, build, run the source web app, and keep the installed DSH separate."
invocation: manual
disable-model-invocation: true
---

# Tom DeepSeek Harness Workflow

<HARD-GATE>
Use the checkout selected by `$DSH_SOURCE_CHECKOUT` (default: `$HOME/work/harness/deepseek-harness`). Do not create sibling clones or run source commands from its parent directory. The expected origin is `https://github.com/monotykamary/deepseek-harness.git`.
</HARD-GATE>

## Core Principle

One source checkout, two planes: edit and run `$DSH_SOURCE_CHECKOUT` as the source plane while the global installed `dsh` stays the untouched stable fallback.

## When to Use / NOT

- **Use when:** working on Tom's DeepSeek Harness source checkout, updating from Tom's remote, editing safely, building, running the source web app.
- **NOT when:** doing normal work with the installed `dsh` distribution (that is the installed plane, not source work), or repairing OpenViking (a separate workflow per the Two-plane rule).

## Two-plane rule

- **Source plane:** edit and run `$DSH_SOURCE_CHECKOUT` with `pnpm dsh web`.
- **Installed plane:** the global `dsh` remains the stable installed distribution. Do not replace it with a local build while source work is in progress.
- OpenViking repairs are a separate workflow; do not change its service or Python environment as part of a harness edit unless explicitly requested.

## Workflow

1. **Orient.**
   ```bash
   DSH_SOURCE_CHECKOUT="${DSH_SOURCE_CHECKOUT:-$HOME/work/harness/deepseek-harness}"
   export DSH_SOURCE_CHECKOUT
   cd "$DSH_SOURCE_CHECKOUT"
   git status --short --branch
   git remote -v
   ```
 Confirm the worktree and remote before touching files. Preserve unrelated changes.

2. **Update safely.**
   ```bash
   git fetch origin --prune
   git switch -c work/<short-name>   # once, if still on master
   git rebase origin/master
   ```
 Fetch never changes the worktree. Commit a WIP save point before rebasing; stash only when a commit is not appropriate.

3. **Install and build.**
   ```bash
   pnpm install --frozen-lockfile
   pnpm run build
   ```
 Do not edit generated `dist/` artifacts by hand. Rebuild after source changes.

4. **Run source without disturbing the installed app.**
   ```bash
   pnpm dsh web --no-open --host 127.0.0.1 --port 43127
   ```
 The web process is intentionally long-lived; a timeout is not a test failure if the HTTP probe is healthy. Restart it after rebuilding.

5. **Verify before claiming success.**
   ```bash
   git diff --check
   pnpm exec vitest run --config vitest.e2e.config.ts apps/cli/tests/built-bin.e2e.ts
   git status --short --branch
   ```
 Add focused tests for the changed package when available.

6. **Integrate.** Commit only reviewed files, then rebase again before pushing. Never force-push shared branches. Use the reference workflow for conflict recovery, profile mismatches, and the stable/source update loop.

## Red Flags

- Sibling clones or a renamed checkout; source commands run from `${DSH_SOURCE_CHECKOUT%/*}` itself (HARD-GATE).
- Replacing the installed `dsh` with a local build while source work is in progress (Two-plane rule).
- Hand-editing generated `dist/` artifacts instead of rebuilding (Workflow step 3).
- Rebasing without a WIP save point commit; stashing when a commit is not inappropriate (Workflow step 2).
- Force-pushing shared branches (Workflow step 6).
- Treating the long-lived web process timeout as a test failure while the HTTP probe is healthy (Workflow step 4).

## Verification

- `git diff --check` is clean; `pnpm exec vitest run --config vitest.e2e.config.ts apps/cli/tests/built-bin.e2e.ts` passes; `git status --short --branch` shows only reviewed changes (Workflow step 5).
- For a running source app: the HTTP probe on port 43127 is healthy (Workflow step 4); verify long-running commands with `curl` on the chosen port (`references/update-while-editing.md`).
- The result-contract report is complete: checkout path, branch and base commit, update action, files changed, build/test evidence, running port, and any uncommitted or unrelated changes.

## Result contract

Report: checkout path, branch and base commit, update action, files changed, build/test evidence, running port, and any uncommitted or unrelated changes.

## References

- `references/update-while-editing.md`, the update-while-editing loop: fetch-during-edit safety, save-point/stash discipline before rebase, the release/update boundary (no global installs mid-edit), and recovery rules for wrong-repo/dirty-worktree/build-failure/pending-plugin cases.
