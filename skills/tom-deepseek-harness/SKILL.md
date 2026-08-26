---
name: tom-deepseek-harness
description: "Use when working on Tom's DeepSeek Harness source checkout: update from Tom's remote, edit safely, build, run the source web app, and keep the installed DSH separate."
disable-model-invocation: true
---

# Tom DeepSeek Harness Workflow

<HARD-GATE>
The only source checkout is `/home/utopia/work/harness/deepseek-harness`. Do not create sibling clones, rename it to another harness directory, or run source commands from `/home/utopia/work/harness` itself. The expected origin is `https://github.com/monotykamary/deepseek-harness.git`.
</HARD-GATE>

## Two-plane rule

- **Source plane:** edit and run `/home/utopia/work/harness/deepseek-harness` with `pnpm dsh web`.
- **Installed plane:** the global `dsh` remains the stable installed distribution. Do not replace it with a local build while source work is in progress.
- OpenViking repairs are a separate workflow; do not change its service or Python environment as part of a harness edit unless explicitly requested.

## Workflow

1. **Orient.**
   ```bash
   cd /home/utopia/work/harness/deepseek-harness
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

## Result contract

Report: checkout path, branch and base commit, update action, files changed, build/test evidence, running port, and any uncommitted or unrelated changes.
