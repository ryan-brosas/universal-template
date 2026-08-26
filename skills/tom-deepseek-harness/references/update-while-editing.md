# Updating Tom's Harness While Editing

## Stable/source separation

Keep the global `dsh` available as the known-good fallback. The editable checkout is:

```text
/home/utopia/work/harness/deepseek-harness
```

Run the source checkout on a separate port. The installed app and the source app may share `$DSH_HOME` only when their versions match; if plugin rows remain pending, stop mixing generations and use an isolated `DSH_HOME` with a matching profile. Never “fix” a source mismatch by overwriting the live installed profile.

## Normal update loop

```bash
cd /home/utopia/work/harness/deepseek-harness
git status --short --branch
git fetch origin --prune
```

`fetch` is safe during an edit and does not change files. If the worktree is clean, fast-forward or rebase:

```bash
git pull --ff-only origin master
# or, on a work branch:
git rebase origin/master
```

If work is in progress, make a save point first:

```bash
git add path/to/owned/files
git commit -m 'wip: preserve harness work'
git fetch origin
git rebase origin/master
```

For genuinely throwaway edits:

```bash
git stash push -u -m 'harness-wip'
git rebase origin/master
git stash pop
```

Resolve conflicts deliberately, inspect `git diff`, run `git diff --check`, then rerun the build and focused tests. Keep commits scoped to the harness; do not stage `.dsh` credentials, sessions, generated output, or unrelated files.

## Edit/build/run loop

```bash
cd /home/utopia/work/harness/deepseek-harness
pnpm install --frozen-lockfile
pnpm run build
pnpm dsh web --no-open --host 127.0.0.1 --port 43127
```

After a code edit, stop the source process, rebuild, and restart. Use the global `dsh` for normal work while the source process is being changed.

## Release/update boundary

Do not run `npm install --global` as part of ordinary source editing. Only install a published release globally after the source build, tests, and manual smoke test pass. Before switching versions, record:

```bash
git rev-parse --short HEAD
git status --short --branch
dsh --version
```

## Recovery rules

- Wrong repository or extra checkout: stop and restore the single required layout; do not silently merge directories.
- Dirty worktree: identify ownership before update; preserve unrelated changes.
- Build failure: inspect the first error, fix or record it, then rerun the smallest affected check.
- Pending plugins: compare source version, profile version, and `$DSH_HOME`; isolate before changing configuration.
- Long-running web command: verify with `curl` on the chosen port; do not treat the still-running process as a hang by itself.
