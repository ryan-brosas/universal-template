<!-- capsule-v2 -->
# PTY environment & shell hooks — how does a daemon spawn a shell that behaves like a login shell without leaking its own terminal identity?

**Source:** localterm MIT `fix/pi-extension-native-import@f26c5853`; Codebase Memory `localterm`. **Question:** How do you build a child PTY environment and per-shell prompt hooks so TUIs render as generic xterm and hooks replay through exec'd wrappers?

## Environment builder — denylist + ZDOTDIR recovery + fresh PATH
**Path/Symbol:** `packages/server/src/build-pty-environment.ts:buildPtyEnvironment` (25–88); `packages/server/src/constants.ts:PTY_ENV_DENYLIST` (242–261).
**Signature:** `buildPtyEnvironment({input, sessionId, inheritedEnvironment = process.env, platform = process.platform}): Record<string, string>`.
**Data Shape:** denylist = localterm control vars (`LOCALTERM_DAEMON_CHILD/INITIAL_COMMAND/SESSION_ID`, `__LOCALTERM_EXEC_DEPTH`) + terminal-identity vars (`TERM_PROGRAM[_VERSION]`, `TERM_SESSION_ID`, `ITERM_*`, `KITTY_*`, `WT_*`, `GHOSTTY_*`, `VSCODE_*`, `ZDOTDIR`).

### Decisive source
```ts
// If we leak e.g. TERM_PROGRAM=ghostty, modern Ink-based TUIs probe for that
// terminal's protocol (kitty keyboard, XTQVERSION, XTGETTCAP, OSC 1337) and —
// when xterm.js doesn't answer — fall back to degraded inline-plain rendering.
// Removing these lets the TUI treat us as a generic xterm-256color. (:235-240)
const isLocaltermPath = (value) =>
  /localterm-(?:zdot|bash)-/.test(value) || value === stableZshHookDir;
const userZdotdirFromEnvironment =
  inheritedZdotdir && !isLocaltermPath(inheritedZdotdir) ? inheritedZdotdir
  : inheritedOriginalZdotdir && !isLocaltermPath(...) ? ... : undefined;
environment.PATH = shellPathForUserShell();   // don't leak the daemon's PATH
```

**Flow:** copy inherited env minus denylist → recover the user's REAL ZDOTDIR (drop values pointing at localterm-owned hook dirs — a stale plist `zsh -l -c` would otherwise make the generated hook source itself; prefer live ZDOTDIR over `__LOCALTERM_ORIG_ZDOTDIR`) → re-pin PATH for the user shell → apply request env → default macOS locale (`DEFAULT_MACOS_PTY_LOCALE`) when unset → set `TERM=xterm-256color`, `COLORTERM`, `LOCALTERM`, session id.
**Invariant:** terminal-identity vars never reach the child; a legit user-set custom ZDOTDIR passes through untouched.
**Probe:** `packages/server/tests/build-pty-environment.test.ts` :115 recovers the real zdotdir over an inherited stable-hook ZDOTDIR, :127 drops it when no original recorded, :147 passes a legitimate user ZDOTDIR through.

## Shell hook builder — eval-not-type initial commands + exec shadowing
**Path/Symbol:** `packages/server/src/shell-hook-builder.ts:ShellHookBuilder.prepare` (30–210); `automationExitHookFunctionLines` (229–245); `zshExecShadowLines` (267–283).
**Signature:** `prepare(shellName, env): [string[], Record<string,string> | null]`; hooked shells = `HOOKED_SHELL_NAMES = {zsh, bash, fish}` (constants.ts:291).
**Data Shape:** zsh → stable per-user hook dir `~/.localterm/zsh-hook` returned as `ZDOTDIR` (+ `__LOCALTERM_ORIG_ZDOTDIR`), mode 0700/0600, deliberately NOT in cleanup paths (exec'd wrapper shells re-source it after this session dies). bash → per-session temp rcfile via `--rcfile`, cleaned up. fish → `-C` init-command string, no temp file.

### Decisive source
```sh
# zsh hook script lines (:53-100):
[[ -n "${__LOCALTERM_HOOK_SOURCED:-}" ]] && return 0   # same-process guard (shell-local)
__LOCALTERM_HOOK_SOURCED=1
source '<user-zdotdir>/.zshenv' ... .zprofile ... .zshrc   # login order
unfunction exec 2>/dev/null || true          # drop exec shadow AFTER rc ran
<path-prepend shims dir AFTER rc>            # shims survive rc PATH manipulation
unsetopt PROMPT_SP                           # kills stray % mark + fill-space wrap bug
# exec shadow (:267-283): zsh resolves functions before builtins, so during rc:
exec() { (( $# == 0 )) || [[ "$1" == -* ]] && builtin exec "$@"
  typeset -x __LOCALTERM_EXEC_DEPTH=$(( ${__LOCALTERM_EXEC_DEPTH:-0} + 1 ))
  typeset -x ZDOTDIR="$__localterm_hook_zdotdir"   # re-pin so wrapper children replay the hook
  builtin exec "$@" }                              # refuses past ZSH_EXEC_SHADOW_MAX_DEPTH = 4
```

**Flow:** initial command for a hooked shell arrives via `LOCALTERM_INITIAL_COMMAND` env (on the denylist so only Session sets it) → prompt hook copies to a local, UNSETS the env var BEFORE eval (children never inherit it; runs once) → prints `+ <cmd>`, emits fg/git-dirty, evals, emits `automation-exit;<status>` → unhooked shells (sh/dash) take the at-spawn PTY write instead.
**Invariant:** a typed-looking initial command must never go through the line editor (no ECHO races/double-echo); shims prepend AFTER user rc so they shadow despite rc PATH edits; the exec shadow is function-scoped so `typeset -x` values are exactly what a successful `exec` replaces the process with.
**Probe:** `tests/shell-hook-builder.test.ts` :73 same-process re-source guard line present, :81 shadows rc-level exec so wrapper child shells re-inherit the hook dir, :94 shadow removed after rc, :103 shims prepended after zshrc, :111 automation hook installed unconditionally/gated at runtime.

## Secret shim line (the thing hooks install)
**Path/Symbol:** `packages/server/src/secret-shims.ts:shimPathPrependLine` (154+).
**Data Shape:** emits a shell-line that prepends the secrets-shims dir to PATH when the dir exists (per-shell quoting: fish escapes `'` as `\'`, not the POSIX `\''` idiom — shell-hook-builder.ts:168-171).

**Get live surrounding code**
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "localterm", name_pattern: "ShellHookBuilder|buildPtyEnvironment|shimPathPrependLine", limit: 8 });
```

## Verdict
Adopt the identity-strip denylist (generic-xterm posture for Ink TUIs), ZDOTDIR poisoning defense, eval-via-hook initial commands with copy-unset-before-eval, post-rc shims ordering, the exec-shadow depth-capped re-pin, and PROMPT_SP disabling; adapt hook dir locations, shell lists, locale defaults, and rc-file orders to host; omit launchd/systemd daemon wiring and the CLI installer commands unless porting the product. Probes cited from on-disk test files (vite-plus; tests excluded from graph index by design).
