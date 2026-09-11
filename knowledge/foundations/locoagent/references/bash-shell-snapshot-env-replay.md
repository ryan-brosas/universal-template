<!-- capsule-v2 -->
# Shell snapshot — capture-once environment replay with ARGV0 tool shims

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you give every spawned command the user's interactive shell state (aliases, functions, options) without a per-command login shell?

## Path/Symbol
**Path/Symbol:** `src/utils/bash/ShellSnapshot.ts` — `createArgv0ShellFunction` (:35-59), `createRipgrepShellIntegration` (:65-92), `getUserSnapshotContent` (aliases/shopt/set -o sections, ~:200-263), `getClaudeCodeSnapshotContent` (:269-340), `getSnapshotScript` (:345-386), `createAndSaveSnapshot` (:413+, `SNAPSHOT_CREATION_TIMEOUT = 10000` :24).
**Signature:** `createAndSaveSnapshot(binShell) → Promise<string | undefined>` — path to a sourced-per-command snapshot file, or undefined on any failure.
**Data Shape:** generated shell script that writes `snapshot-<type>-<ts>-<rand>.sh` containing: unalias -a → user rc content → shopt/set -o replays (`shopt -s expand_aliases` forced) → filtered aliases (winpty excluded on Windows) → rg availability check + fallback alias/function → PATH export.

### Decisive source
```ts
//      # When this file is sourced, we first unalias to avoid conflicts
//      # This is necessary because aliases get "frozen" inside function definitions at definition time,
//      # which can cause unexpected behavior when functions use commands that conflict with aliases
//      echo "unalias -a 2>/dev/null || true" >> "$SNAPSHOT_FILE"
```

**Flow:** detect config file (.zshrc/.bashrc/…) → generate a script that sources it ONCE under `-c -l` with `< /dev/null`, GIT_EDITOR=true, CLAUDECODE=1 → the script replays captured state INTO the snapshot file (aliases via `alias | sed … | head -n 1000`, options via `shopt -p | head -n 1000` and `set -o | grep on`) → embedded-tool shims: for embedded ripgrep write an argv0-dispatch FUNCTION (bun checks its argv[0]; zsh/msys use `ARGV0=<name> bin args`, real bash uses `exec -a`; subshell variant avoids replacing interactive parent), for system rg a plain alias guarded by `(unalias rg; command -v rg)` so user aliases don't shadow the availability check → ant builds additionally SHADOW find/grep with bfs/ugrep functions injecting `-regextype findutils-default`. Snapshot creation failure degrades to undefined; provider falls back to login shells (see bash-shell-provider capsule).

**Invariant:** (1) Aliases freeze inside function bodies AT DEFINITION TIME — hence `unalias -a` leads every replay. (2) Alias expansion needs `shopt -s expand_aliases` forced in the replay even if user config had it off. (3) Availability probes must run in an alias-killing subshell or user aliases mask the real binary check. (4) argv0 dispatch has THREE platform variants (zsh env-var / msys-cygwin env-var / bash exec -a) plus a subshell form — picking one breaks two platforms. (5) Everything is best-effort: timeout 10 s, 1 MB buffer, never crash the session over snapshot loss.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF 'aliases get "frozen" inside function definitions' src/utils/bash/ShellSnapshot.ts` → :369; `grep -nF 'exec -a' src/utils/bash/ShellSnapshot.ts | head -1` → :49; `grep -nF 'SNAPSHOT_CREATION_TIMEOUT = 10000' src/utils/bash/ShellSnapshot.ts` → :24; graph resolves createAndSaveSnapshot/createRipgrepShellIntegration line-exact.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createAndSaveSnapshot createArgv0ShellFunction getSnapshotScript", limit: 5 });
```

## Verdict
Adopt the generate-script/replay-file architecture with its ordering (unalias → user content → options → forced expand_aliases → aliases → shims → PATH). Shim platform matrix ports as-is for bun-style embedded tools.
