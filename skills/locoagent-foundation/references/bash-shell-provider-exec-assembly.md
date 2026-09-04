<!-- capsule-v2 -->
# Bash shell provider — eval-wrap assembly with snapshot fallback and stdin-redirect placement

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you assemble the actual spawn string for a user bash command so it inherits an interactive-like environment, survives snapshot loss, and keeps redirects attached to the right command?

## Path/Symbol
**Path/Symbol:** `src/utils/shell/bashProvider.ts` — `getDisableExtglobCommand` (:39-56), `createBashShellProvider` (:58-255), buildExecCommand (:77-198), getSpawnArgs login-shell fallback (:200-206), tmux/sandbox env overrides (:208-253); helpers `rearrangePipeCommand` (bashPipeCommand.ts), `quoteShellCommand`/`rewriteWindowsNullRedirect` (shellQuoting.ts).
**Signature:** `buildExecCommand(command, {id, sandboxTmpDir, useSandbox}) → {commandString, cwdFilePath}`; `getSpawnArgs(cmd) → ['-c', ...('-l'), cmd]`.
**Data Shape:** `&& `-joined parts: source snapshot → session env script → extglob-off → `eval '<quoted command>'` → `pwd -P >| <cwdFile>`.

### Decisive source
```ts
// This access() check is NOT pure TOCTOU — it's the fallback decision
// point for getSpawnArgs. When the snapshot disappears mid-session
// (tmpdir cleanup), we must clear lastSnapshotFilePath so getSpawnArgs
// adds -l and the command gets login-shell init. Without this check,
// `source ... || true` silently fails and commands run with NO shell
// init (neither snapshot env nor login profile). The `|| true` on source
// still guards the race between this check and the spawned shell.
```

**Flow:** snapshot promise created once (10 s timeout, failure ⇒ undefined); per command: re-verify snapshot file exists — missing ⇒ clear lastSnapshotFilePath so THIS command falls back to a LOGIN shell (`-l`) instead of sourcing nothing; assemble `source snapshot || true`, session env script, extglob disable (`shopt -u extglob` for bash / `setopt NO_EXTENDED_GLOB` for zsh — extended globs expand malicious filenames AFTER validation; when CLAUDE_CODE_SHELL_PREFIX may swap shells emit BOTH forms because zsh's command_not_found_handler writes to stdout), then `eval 'command'` single-quoted for alias expansion after source, then physical-cwd capture. Pipes with added stdin redirect are REARRANGED (`cmd1 | cmd2 < /dev/null` ⇒ `cmd1 < /dev/null | cmd2`) because eval would attach stdin to eval itself and rg-with-no-path waits forever on the open pipe. Windows CMD-style `>nul` rewritten to `/dev/null` (#4928: literal `nul` file breaks git).

**Invariant:** (1) The pre-execution access() check is a FALLBACK DECISION, not TOCTOU hygiene — its output selects between snapshot-source and login-init for THIS spawn. (2) `eval` wrapping is required for aliases to be visible post-source (second parse pass) — which is why the inner command must be single-quote escaped and stdin redirects moved into the pipeline head. (3) Extended globbing must be disabled AFTER user config sourcing or it gets re-enabled. (4) Env overrides (sandbox TMPDIR/TMPPREFIX, session vars, isolated TMUX socket) apply at spawn-env level, never by textual prefixing.

**Probe:** coverage caveat — no upstream unit tests. Pins: `grep -nF "it's the fallback decision" src/utils/shell/bashProvider.ts` → :86; `grep -nF 'waits on the open spawn stdin pipe' src/utils/shell/bashProvider.ts` → :149; `grep -nF 'expand after our security validation' src/utils/shell/bashProvider.ts` → :30; graph `search_graph --project locoagent --query createBashShellProvider rearrangePipeCommand` line-exact :58-255 / :14-100.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "createBashShellProvider buildExecCommand getSpawnArgs rewriteWindowsNullRedirect", limit: 5 });
```

## Verdict
Adopt the assembly order and the three guards (snapshot-fallback decision, extglob-off-after-sourcing, pipe-head stdin move) for any eval-wrapping shell provider.
